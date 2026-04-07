param(
    [string[]]$ScriptLine,
    [switch]$NoLoop,
    [switch]$ServeOnly,
    [switch]$NoServer,
    [switch]$Stop,
    [int]$Port,
    [string]$ApiKey
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TerminalScriptPath = $MyInvocation.MyCommand.Path
$StateDir = Join-Path $BaseDir "openai_unlimited_terminal_data"
$StatePath = Join-Path $StateDir "state.json"
$ServerConfigPath = Join-Path $StateDir "server.json"
$ApiSessionsPath = Join-Path $StateDir "api_sessions.json"
$ModelsCachePath = Join-Path $StateDir "models_cache.json"
$TerminalInfoPath = Join-Path $StateDir "terminal.json"
$BaseUrl = "https://android.chat.openai.com/backend-anon"
$UserAgent = "ChatGPT/1.2026.069 (Android 14; Mobile; rv:0)"
$Language = "en-US"
$DefaultPort = 12434
$DefaultApiKey = "openai-unlimited-local"
$DefaultSessionMode = "stateless"

Add-Type -AssemblyName System.Net.Http

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Save-TextFile {
    param(
        [string]$Path,
        [string]$Content
    )
    Ensure-Directory -Path (Split-Path -Parent $Path)
    for ($i = 0; $i -lt 10; $i++) {
        try {
            [System.IO.File]::WriteAllText($Path, $Content, [System.Text.UTF8Encoding]::new($false))
            return
        }
        catch {
            if ($i -eq 9) {
                throw
            }
            Start-Sleep -Milliseconds 150
        }
    }
}

function ConvertTo-CompactJson {
    param($Value)
    return ($Value | ConvertTo-Json -Depth 20 -Compress)
}

function New-DeviceId {
    [guid]::NewGuid().ToString()
}

function Get-DefaultState {
    [pscustomobject]@{
        device_id = New-DeviceId
        model = "auto"
        conversation_id = $null
        parent_message_id = $null
        last_assistant_message_id = $null
        last_tools = @()
        last_title = $null
    }
}

function Load-State {
    Ensure-Directory -Path $StateDir
    if (-not (Test-Path -LiteralPath $StatePath)) {
        $state = Get-DefaultState
        Save-State -State $state
        return $state
    }
    $raw = Get-Content -LiteralPath $StatePath -Raw
    if ([string]::IsNullOrWhiteSpace($raw)) {
        $state = Get-DefaultState
        Save-State -State $state
        return $state
    }
    $state = $raw | ConvertFrom-Json
    if (-not $state.device_id) {
        $state.device_id = New-DeviceId
    }
    if (-not $state.model) {
        $state.model = "auto"
    }
    if (-not $state.PSObject.Properties["last_tools"]) {
        $state.last_tools = @()
    }
    return $state
}

function Save-State {
    param($State)
    Save-TextFile -Path $StatePath -Content (ConvertTo-CompactJson -Value $State)
}

function Remove-TextFile {
    param([string]$Path)
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    }
}

function Get-TerminalMode {
    if ($ServeOnly) {
        return "server_only"
    }
    if ($NoServer) {
        return "terminal_no_server"
    }
    return "terminal"
}

function Save-TerminalInfo {
    param($ServerConfig)
    $terminalInfo = [pscustomobject]@{
        pid = $PID
        port = [int]$ServerConfig.port
        api_key = [string]$ServerConfig.api_key
        started_at = (Get-Date).ToUniversalTime().ToString("o")
        mode = Get-TerminalMode
    }
    Save-TextFile -Path $TerminalInfoPath -Content (ConvertTo-CompactJson -Value $terminalInfo)
}

function Load-TerminalInfo {
    if (-not (Test-Path -LiteralPath $TerminalInfoPath)) {
        return $null
    }
    $raw = Get-Content -LiteralPath $TerminalInfoPath -Raw
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return $null
    }
    return ($raw | ConvertFrom-Json)
}

function Remove-TerminalInfo {
    Remove-TextFile -Path $TerminalInfoPath
}

function Stop-RunningTerminal {
    $terminalInfo = Load-TerminalInfo
    if (-not $terminalInfo) {
        $serverConfig = Load-ServerConfig -PortOverride 0 -ApiKeyOverride $null
        if ($serverConfig -and (Test-LocalApiServerAlive -Port ([int]$serverConfig.port))) {
            try {
                Stop-LocalApiServerByPortAndKey -Port ([int]$serverConfig.port) -ApiKey ([string]$serverConfig.api_key)
            }
            catch {}
            if (-not (Test-LocalApiServerAlive -Port ([int]$serverConfig.port))) {
                Write-Host "terminal=stopped"
                return
            }
            Write-Host "terminal=stop_failed"
            return
        }
        Write-Host "terminal=not_running"
        return
    }

    $targetPid = 0
    $hadServer = $false
    try {
        $targetPid = [int]$terminalInfo.pid
    }
    catch {
        $targetPid = 0
    }

    if ($terminalInfo.port) {
        $hadServer = Test-LocalApiServerAlive -Port ([int]$terminalInfo.port)
    }

    try {
        if ($terminalInfo.port -and $terminalInfo.api_key) {
            Stop-LocalApiServerByPortAndKey -Port ([int]$terminalInfo.port) -ApiKey ([string]$terminalInfo.api_key)
        }
    }
    catch {}

    $process = $null
    if ($targetPid -gt 0) {
        $process = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
    }

    if ($process) {
        try {
            Stop-Process -Id $targetPid -Force -ErrorAction Stop
            Wait-Process -Id $targetPid -Timeout 5 -ErrorAction SilentlyContinue
        }
        catch {}
    }

    Start-Sleep -Milliseconds 800

    $remainingProcess = $null
    if ($targetPid -gt 0) {
        $remainingProcess = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
    }
    $serverStillRunning = $false
    if ($terminalInfo.port) {
        $serverStillRunning = Test-LocalApiServerAlive -Port ([int]$terminalInfo.port)
    }

    if (-not $remainingProcess -and -not $serverStillRunning) {
        Remove-TerminalInfo
    }

    if ($remainingProcess -or $serverStillRunning) {
        Write-Host "terminal=stop_failed"
        return
    }

    if ($process -or $hadServer) {
        Write-Host "terminal=stopped"
        return
    }

    Write-Host "terminal=not_running"
}

function New-HttpClient {
    $handler = [System.Net.Http.HttpClientHandler]::new()
    $handler.AutomaticDecompression = [System.Net.DecompressionMethods]::GZip -bor [System.Net.DecompressionMethods]::Deflate
    $client = [System.Net.Http.HttpClient]::new($handler)
    $client.Timeout = [TimeSpan]::FromMinutes(5)
    $client.DefaultRequestHeaders.TryAddWithoutValidation("User-Agent", $UserAgent) | Out-Null
    $client.DefaultRequestHeaders.TryAddWithoutValidation("Oai-Language", $Language) | Out-Null
    return $client
}

function Get-Models {
    param(
        $State,
        [switch]$PreferCache
    )
    $cache = Load-ModelsCache
    if ($PreferCache -and $cache.response -and $cache.fetched_at) {
        $age = Get-ModelsCacheAgeSeconds
        if ($age -ne $null -and $age -lt 60) {
            return $cache.response
        }
    }
    $client = New-HttpClient
    try {
        $client.DefaultRequestHeaders.Remove("Oai-Device-Id") | Out-Null
        $client.DefaultRequestHeaders.TryAddWithoutValidation("Oai-Device-Id", [string]$State.device_id) | Out-Null
        $response = $client.GetAsync("$BaseUrl/models").GetAwaiter().GetResult()
        $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) {
            throw "models failed: $([int]$response.StatusCode) $body"
        }
        $models = $body | ConvertFrom-Json
        Save-ModelsCache -Response $models
        return $models
    }
    finally {
        $client.Dispose()
    }
}

function Show-Models {
    param($Models)
    $defaultSlug = [string]$Models.default_model_slug
    foreach ($model in $Models.models) {
        $slug = [string]$model.slug
        $reasoning = [string]$model.reasoning_type
        $title = [string]$model.title
        $maxTokens = if ($model.PSObject.Properties["max_tokens"] -and $model.max_tokens) { [string]$model.max_tokens } else { "unknown" }
        $description = if ($model.PSObject.Properties["description"] -and $model.description) { [string]$model.description } else { "" }
        $tags = @()
        if ($model.PSObject.Properties["tags"] -and $model.tags) {
            $tags = @($model.tags)
        }
        $tools = @()
        if ($model.enabled_tools) {
            $tools = @($model.enabled_tools)
        }
        $mark = if ($slug -eq $defaultSlug) { "*" } else { "-" }
        $toolText = if ($tools.Count -gt 0) { ($tools -join ",") } else { "none" }
        $tagText = if ($tags.Count -gt 0) { ($tags -join ",") } else { "none" }
        Write-Host "$mark $slug | $title"
        Write-Host "  max_tokens=$maxTokens | reasoning=$reasoning"
        Write-Host "  active_tools=$toolText"
        Write-Host "  tags=$tagText"
        if (-not [string]::IsNullOrWhiteSpace($description)) {
            Write-Host "  description=$description"
        }
    }
}

function Show-Categories {
    param($Models)
    foreach ($category in $Models.categories) {
        $name = [string]$category.category
        $defaultModel = [string]$category.default_model
        $features = @()
        if ($category.supported_features) {
            $features = @($category.supported_features)
        }
        $featureText = if ($features.Count -gt 0) { ($features -join ",") } else { "none" }
        Write-Host "- $name | default=$defaultModel | features=$featureText"
    }
}

function Set-Model {
    param(
        $State,
        [string]$Slug
    )
    $models = Get-Models -State $State
    $match = @($models.models | Where-Object { $_.slug -eq $Slug })
    if ($match.Count -eq 0) {
        throw "unknown model: $Slug"
    }
    $State.model = $Slug
    $State.last_tools = @($match[0].enabled_tools)
    Save-State -State $State
    Write-Host "model=$Slug"
    if ($State.last_tools.Count -gt 0) {
        Write-Host "active_tools=$($State.last_tools -join ',')"
    }
}

function Sync-ModelTools {
    param($State)
    $models = Get-Models -State $State
    $match = @($models.models | Where-Object { $_.slug -eq $State.model })
    if ($match.Count -gt 0 -and $match[0].enabled_tools) {
        $State.last_tools = @($match[0].enabled_tools)
        Save-State -State $State
    }
}

function Reset-Conversation {
    param($State)
    $State.conversation_id = $null
    $State.parent_message_id = $null
    $State.last_assistant_message_id = $null
    $State.last_title = $null
    Save-State -State $State
    Write-Host "conversation=reset"
}

function Show-State {
    param($State)
    $conv = if ($State.conversation_id) { $State.conversation_id } else { "none" }
    $parent = if ($State.parent_message_id) { $State.parent_message_id } else { "none" }
    $tools = if ($State.last_tools -and @($State.last_tools).Count -gt 0) { (@($State.last_tools) -join ",") } else { "unknown" }
    $modelInfo = $null
    try {
        $models = Get-Models -State $State -PreferCache
        $matches = @($models.models | Where-Object { $_.slug -eq $State.model })
        if ($matches.Count -gt 0) {
            $modelInfo = $matches[0]
        }
    }
    catch {}
    Write-Host "device_id=$($State.device_id)"
    Write-Host "model=$($State.model)"
    if ($modelInfo) {
        $title = if ($modelInfo.title) { [string]$modelInfo.title } else { "unknown" }
        $reasoning = if ($modelInfo.reasoning_type) { [string]$modelInfo.reasoning_type } else { "unknown" }
        $maxTokens = if ($modelInfo.max_tokens) { [string]$modelInfo.max_tokens } else { "unknown" }
        Write-Host "model_title=$title"
        Write-Host "max_tokens=$maxTokens"
        Write-Host "reasoning=$reasoning"
    }
    Write-Host "conversation_id=$conv"
    Write-Host "parent_message_id=$parent"
    Write-Host "active_tools=$tools"
}

function New-ConversationStateFrom {
    param(
        $State,
        [string]$Model
    )
    return [pscustomobject]@{
        device_id = [string]$State.device_id
        model = $Model
        conversation_id = $null
        parent_message_id = $null
        last_assistant_message_id = $null
        last_tools = @()
        last_title = $null
    }
}

function Test-SearchIntent {
    param([string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $false
    }
    $pattern = '(?i)\b(weather|temperature|forecast|rain|snow|today|tomorrow|current|currently|latest|recent|news|headline|price|stock|crypto|btc|eth|score|scores|result|results|schedule|standings|president|prime minister|ceo|exchange rate|traffic|flight|flights)\b'
    return ([regex]::IsMatch($Text, $pattern))
}

function Build-SearchAwarePrompt {
    param(
        [string]$Prompt,
        [string[]]$Tools
    )
    $toolList = if ($Tools) { @($Tools) } else { @() }
    $hasSearch = ($toolList -contains "search")
    if (-not $hasSearch -or -not (Test-SearchIntent -Text $Prompt)) {
        return $Prompt
    }
    return @"
Use live web search for this request.
Do not guess.
If current information is needed, search first and answer with the fetched result.

User request:
$Prompt
"@
}

function Send-Conversation {
    param(
        $State,
        [string]$Prompt
    )
    if (-not $State.last_tools -or @($State.last_tools).Count -eq 0) {
        Sync-ModelTools -State $State
    }
    $effectivePrompt = Build-SearchAwarePrompt -Prompt $Prompt -Tools $State.last_tools
    $result = Invoke-AnonymousConversation -State $State -Prompt $effectivePrompt -PrintChunks
    Write-Host ""
    Apply-ConversationResultToState -State $State -Result $result
    Save-State -State $State
}

function Show-Help {
    Write-Host "/models"
    Write-Host "/categories"
    Write-Host "/model <slug>"
    Write-Host "/state"
    Write-Host "/new"
    Write-Host "/device-reset"
    Write-Host "/help"
    Write-Host "/exit"
}

function Reset-Device {
    param($State)
    $State.device_id = New-DeviceId
    Reset-Conversation -State $State
    Save-State -State $State
    Write-Host "device_id=$($State.device_id)"
}

function Save-SharedJson {
    param(
        [string]$Path,
        $Value
    )
    Ensure-Directory -Path (Split-Path -Parent $Path)
    Save-TextFile -Path $Path -Content (ConvertTo-CompactJson -Value $Value)
}

function Get-DefaultServerConfig {
    return [pscustomobject]@{
        port = $DefaultPort
        api_key = $DefaultApiKey
        autostart_server = $true
        default_session_mode = $DefaultSessionMode
    }
}

function Load-ServerConfig {
    param(
        [int]$PortOverride,
        [string]$ApiKeyOverride
    )
    Ensure-Directory -Path $StateDir
    $config = $null
    $shouldSave = $false
    if (Test-Path -LiteralPath $ServerConfigPath) {
        $raw = Get-Content -LiteralPath $ServerConfigPath -Raw
        if (-not [string]::IsNullOrWhiteSpace($raw)) {
            $config = $raw | ConvertFrom-Json
        }
    }
    if (-not $config) {
        $config = Get-DefaultServerConfig
        $shouldSave = $true
    }
    if (-not $config.PSObject.Properties["port"] -or -not $config.port) {
        $config.port = $DefaultPort
        $shouldSave = $true
    }
    if (-not $config.PSObject.Properties["api_key"] -or [string]::IsNullOrWhiteSpace([string]$config.api_key)) {
        $config.api_key = $DefaultApiKey
        $shouldSave = $true
    }
    elseif ([string]$config.api_key -match '^guest-') {
        $config.api_key = $DefaultApiKey
        $shouldSave = $true
    }
    if (-not $config.PSObject.Properties["autostart_server"]) {
        $config.autostart_server = $true
        $shouldSave = $true
    }
    if (-not $config.PSObject.Properties["default_session_mode"] -or [string]::IsNullOrWhiteSpace([string]$config.default_session_mode)) {
        $config.default_session_mode = $DefaultSessionMode
        $shouldSave = $true
    }
    if ($PortOverride -gt 0) {
        $config.port = $PortOverride
        $shouldSave = $true
    }
    if (-not [string]::IsNullOrWhiteSpace($ApiKeyOverride)) {
        $config.api_key = $ApiKeyOverride
        $shouldSave = $true
    }
    if ($shouldSave) {
        Save-SharedJson -Path $ServerConfigPath -Value $config
    }
    return $config
}

function Load-ApiSessions {
    Ensure-Directory -Path $StateDir
    $store = $null
    if (Test-Path -LiteralPath $ApiSessionsPath) {
        $raw = Get-Content -LiteralPath $ApiSessionsPath -Raw
        if (-not [string]::IsNullOrWhiteSpace($raw)) {
            $store = $raw | ConvertFrom-Json
        }
    }
    if (-not $store) {
        $store = [pscustomobject]@{ sessions = @() }
        Save-SharedJson -Path $ApiSessionsPath -Value $store
    }
    if (-not $store.PSObject.Properties["sessions"]) {
        $store.sessions = @()
    }
    return $store
}

function Save-ApiSessionRecord {
    param($Store, $Session)
    $Store.sessions = @(@($Store.sessions | Where-Object { $_.key -ne $Session.key }) + $Session)
    Save-SharedJson -Path $ApiSessionsPath -Value $Store
}

function Get-ApiSession {
    param($Store, [string]$Key)
    foreach ($session in @($Store.sessions)) {
        if ($session.key -eq $Key) {
            return $session
        }
    }
    return $null
}

function Load-ModelsCache {
    $cache = $null
    if (Test-Path -LiteralPath $ModelsCachePath) {
        $raw = Get-Content -LiteralPath $ModelsCachePath -Raw
        if (-not [string]::IsNullOrWhiteSpace($raw)) {
            $cache = $raw | ConvertFrom-Json
        }
    }
    if (-not $cache) {
        return [pscustomobject]@{ fetched_at = $null; response = $null }
    }
    return $cache
}

function Convert-ToObjectArray {
    param($Value)
    if ($null -eq $Value) {
        return @()
    }
    if ($Value -is [System.Array]) {
        return @($Value)
    }
    if ($Value -is [System.Collections.IEnumerable] -and -not ($Value -is [string])) {
        return @($Value)
    }
    return @($Value)
}

function Save-ModelsCache {
    param($Response)
    Save-SharedJson -Path $ModelsCachePath -Value ([pscustomobject]@{
        fetched_at = (Get-Date).ToUniversalTime().ToString("o")
        response = $Response
    })
}

function Get-ModelsCacheAgeSeconds {
    $cache = Load-ModelsCache
    if (-not $cache.fetched_at) {
        return $null
    }
    try {
        $then = [datetimeoffset]::Parse([string]$cache.fetched_at)
        return [int][Math]::Max(0, (([datetimeoffset]::UtcNow - $then).TotalSeconds))
    }
    catch {
        return $null
    }
}

function Convert-ContentToString {
    param($Content)
    if ($null -eq $Content) { return "" }
    if ($Content -is [string]) { return [string]$Content }
    if ($Content -is [System.Array] -or $Content -is [System.Collections.IEnumerable]) {
        $parts = @()
        foreach ($item in $Content) {
            if ($null -eq $item) { continue }
            if ($item -is [string]) { $parts += [string]$item }
            elseif ($item.PSObject -and $item.PSObject.Properties["text"]) { $parts += [string]$item.text }
            else { $parts += (ConvertTo-CompactJson -Value $item) }
        }
        return ($parts -join "`n")
    }
    if ($Content.PSObject -and $Content.PSObject.Properties["text"]) { return [string]$Content.text }
    return (ConvertTo-CompactJson -Value $Content)
}

function Apply-ConversationResultToState {
    param($State, $Result)
    if ($Result.conversation_id) { $State.conversation_id = [string]$Result.conversation_id }
    if ($Result.parent_message_id) {
        $State.parent_message_id = [string]$Result.parent_message_id
        $State.last_assistant_message_id = [string]$Result.parent_message_id
    }
    if ($Result.last_title) { $State.last_title = [string]$Result.last_title }
    if ($Result.last_tools) { $State.last_tools = @($Result.last_tools) }
}

function Invoke-AnonymousConversation {
    param(
        $State,
        [string]$Prompt,
        [switch]$PrintChunks
    )
    $client = New-HttpClient
    $reader = $null
    $stream = $null
    $response = $null
    try {
        $client.DefaultRequestHeaders.Remove("Oai-Device-Id") | Out-Null
        $client.DefaultRequestHeaders.TryAddWithoutValidation("Oai-Device-Id", [string]$State.device_id) | Out-Null
        $client.DefaultRequestHeaders.Accept.Clear()
        $client.DefaultRequestHeaders.Accept.ParseAdd("text/event-stream")
        $messageId = [guid]::NewGuid().ToString()
        $parentId = if ($State.parent_message_id) { [string]$State.parent_message_id } else { [guid]::NewGuid().ToString() }
        $payload = [ordered]@{
            action = "next"
            messages = @([ordered]@{
                id = $messageId
                author = [ordered]@{ role = "user" }
                content = [ordered]@{ content_type = "text"; parts = @($Prompt) }
            })
            parent_message_id = $parentId
            model = [string]$State.model
            history_and_training_disabled = $true
        }
        if ($State.conversation_id) { $payload.conversation_id = [string]$State.conversation_id }
        $content = [System.Net.Http.StringContent]::new((ConvertTo-CompactJson -Value $payload), [System.Text.Encoding]::UTF8, "application/json")
        $response = $client.PostAsync("$BaseUrl/conversation", $content, [System.Threading.CancellationToken]::None).GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) {
            throw "conversation failed: $([int]$response.StatusCode) $($response.Content.ReadAsStringAsync().GetAwaiter().GetResult())"
        }
        $stream = $response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
        $reader = [System.IO.StreamReader]::new($stream)
        $text = ""
        $conversationId = $State.conversation_id
        $assistantId = $null
        $title = $null
        $tools = if ($State.last_tools) { @($State.last_tools) } else { @() }
        while (-not $reader.EndOfStream) {
            $line = $reader.ReadLine()
            if ([string]::IsNullOrWhiteSpace($line) -or -not $line.StartsWith("data: ")) { continue }
            $data = $line.Substring(6)
            if ($data -eq "[DONE]") { break }
            try { $event = $data | ConvertFrom-Json } catch { continue }
            if ($event.PSObject.Properties["conversation_id"] -and $event.conversation_id) { $conversationId = [string]$event.conversation_id }
            if ($event.PSObject.Properties["type"] -and $event.type -eq "title_generation" -and $event.title) { $title = [string]$event.title }
            if ($event.PSObject.Properties["type"] -and $event.type -eq "server_ste_metadata" -and $event.metadata -and $event.metadata.is_search -eq $true) {
                $tools = @($tools + "search")
            }
            if ($event.PSObject.Properties["message"] -and $event.message -and $event.message.author.role -eq "assistant") {
                $assistantId = [string]$event.message.id
                $next = if ($event.message.content -and $event.message.content.parts) { [string](Convert-ContentToString -Content $event.message.content.parts) } else { "" }
                if (-not [string]::IsNullOrEmpty($next) -and $next.Length -ge $text.Length) {
                    $delta = $next.Substring($text.Length)
                    if ($PrintChunks -and $delta.Length -gt 0) { Write-Host -NoNewline $delta }
                    $text = $next
                }
            }
        }
        return [pscustomobject]@{
            assistant_text = $text
            conversation_id = $conversationId
            parent_message_id = $assistantId
            last_assistant_message_id = $assistantId
            last_tools = @($tools | Select-Object -Unique)
            last_title = $title
        }
    }
    finally {
        if ($reader) { $reader.Dispose() }
        if ($stream) { $stream.Dispose() }
        if ($response) { $response.Dispose() }
        $client.Dispose()
    }
}

function Get-MessageFingerprints {
    param($Messages)
    return @($Messages | ForEach-Object { ConvertTo-CompactJson -Value $_ })
}

function Convert-MessagesToPrompt {
    param($Messages, [string]$Model, $Tools, $ToolChoice)
    $toolArray = @(Convert-ToObjectArray -Value $Tools | Where-Object { $null -ne $_ })
    $toolMode = (@($toolArray).Count -gt 0 -and $ToolChoice -ne "none")
    $toolNames = @($toolArray | ForEach-Object {
        if ($_ -and $_.PSObject.Properties["function"] -and $_.function -and $_.function.name) {
            [string]$_.function.name
        }
        elseif ($_ -is [string]) {
            [string]$_
        }
    } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    $lines = @("Requested model: $Model")
    $combinedUserText = @($Messages | Where-Object { $_.role -eq "user" } | ForEach-Object { Convert-ContentToString -Content $_.content }) -join "`n"
    if (Test-SearchIntent -Text $combinedUserText) {
        $lines += "Current information is requested."
        if ($toolNames -contains "search") {
            $lines += "Use live search before answering. Do not guess."
        }
        else {
            $lines += "If browsing is unavailable, say current information could not be fetched."
        }
    }
    if ($toolMode) {
        $lines += 'Return only minified JSON.'
        $lines += '{"assistant_text":string|null,"tool_calls":[{"id":"call_x","type":"function","function":{"name":"tool_name","arguments":"{\"key\":\"value\"}"}}]}'
        $lines += "Use tool_calls only when needed. Otherwise set assistant_text."
        if ($ToolChoice -eq "required") { $lines += "You must call at least one tool." }
        $lines += "Available tools:"
        foreach ($tool in $toolArray) {
            $toolFunction = if ($tool.PSObject.Properties["function"]) { $tool.function } else { $null }
            $name = if ($toolFunction -and $toolFunction.name) { [string]$toolFunction.name } else { "unknown_tool" }
            $lines += "- $name"
            if ($toolFunction -and $toolFunction.description) { $lines += "  description: $([string]$toolFunction.description)" }
            if ($toolFunction -and $toolFunction.parameters) { $lines += "  parameters: $(ConvertTo-CompactJson -Value $toolFunction.parameters)" }
        }
    }
    else {
        $lines += "Respond in normal assistant text."
    }
    $lines += "Conversation:"
    foreach ($message in @($Messages)) {
        $role = if ($message.role) { [string]$message.role } else { "user" }
        $text = Convert-ContentToString -Content $message.content
        switch ($role) {
            "system" { $lines += "[SYSTEM]"; $lines += $text }
            "developer" { $lines += "[SYSTEM]"; $lines += $text }
            "user" { $lines += "[USER]"; $lines += $text }
            "assistant" {
                if ($message.PSObject.Properties["tool_calls"] -and $message.tool_calls) { $lines += "[ASSISTANT_TOOL_CALLS]"; $lines += (ConvertTo-CompactJson -Value $message.tool_calls) }
                if (-not [string]::IsNullOrWhiteSpace($text)) { $lines += "[ASSISTANT]"; $lines += $text }
            }
            "tool" {
                $name = if ($message.PSObject.Properties["name"] -and $message.name) { [string]$message.name } else { "tool" }
                $id = if ($message.PSObject.Properties["tool_call_id"] -and $message.tool_call_id) { [string]$message.tool_call_id } else { "" }
                $lines += "[TOOL name=$name id=$id]"
                $lines += $text
            }
            default { $lines += "[$role]"; $lines += $text }
        }
    }
    return ($lines -join "`n")
}

function Get-SessionKeyFromRequest { param($Request, $Body) if ($Request.Headers["X-Guest-Session-Id"]) { return [string]$Request.Headers["X-Guest-Session-Id"] } if ($Body.PSObject.Properties["user"] -and $Body.user) { return [string]$Body.user } return $null }
function Reset-ApiSessionContinuation { param($Session) $Session.conversation_id = $null; $Session.parent_message_id = $null; $Session.last_assistant_message_id = $null; $Session.history_fingerprints = @() }

function Get-SessionPromptMessages {
    param($Session, $Messages)
    $current = @($Messages)
    $fingerprints = @(Get-MessageFingerprints -Messages $current)
    if (-not $Session -or -not $Session.history_fingerprints -or @($Session.history_fingerprints).Count -eq 0) {
        return [pscustomobject]@{ prompt_messages = $current; history_fingerprints = $fingerprints }
    }
    $stored = @($Session.history_fingerprints)
    $prefix = (@($fingerprints).Count -ge @($stored).Count)
    if ($prefix) { for ($i = 0; $i -lt @($stored).Count; $i++) { if ($stored[$i] -ne $fingerprints[$i]) { $prefix = $false; break } } }
    if ($prefix -and @($fingerprints).Count -gt @($stored).Count) {
        return [pscustomobject]@{ prompt_messages = @($current[@($stored).Count..(@($current).Count - 1)]); history_fingerprints = $fingerprints }
    }
    Reset-ApiSessionContinuation -Session $Session
    return [pscustomobject]@{ prompt_messages = $current; history_fingerprints = $fingerprints }
}

function Try-ParseToolEnvelope {
    param([string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $null }
    $trim = $Text.Trim()
    if (-not $trim.StartsWith("{")) { return $null }
    try { $parsed = $trim | ConvertFrom-Json } catch { return $null }
    if (-not $parsed.PSObject.Properties["assistant_text"] -and -not $parsed.PSObject.Properties["tool_calls"]) { return $null }
    $toolCalls = @()
    foreach ($call in @($parsed.tool_calls)) {
        $callFunction = if ($call.PSObject.Properties["function"]) { $call.function } else { $null }
        $name = if ($callFunction -and $callFunction.name) { [string]$callFunction.name } elseif ($call.PSObject.Properties["name"] -and $call.name) { [string]$call.name } else { $null }
        if (-not $name) { continue }
        $args = if ($callFunction -and $callFunction.arguments) { $callFunction.arguments } elseif ($call.PSObject.Properties["arguments"] -and $call.arguments) { $call.arguments } else { "{}" }
        if (-not ($args -is [string])) { $args = ConvertTo-CompactJson -Value $args }
        $toolCalls += [pscustomobject]@{ id = $(if ($call.PSObject.Properties["id"] -and $call.id) { [string]$call.id } else { "call_$([guid]::NewGuid().ToString('N').Substring(0,24))" }); type = "function"; function = [pscustomobject]@{ name = $name; arguments = [string]$args } }
    }
    return [pscustomobject]@{ assistant_text = $(if ($parsed.PSObject.Properties["assistant_text"]) { [string]$parsed.assistant_text } else { $null }); tool_calls = $toolCalls }
}

function Set-CommonApiHeaders { param($Response) $Response.Headers["Access-Control-Allow-Origin"] = "*"; $Response.Headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Guest-Session-Id"; $Response.Headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS" }
function New-ApiErrorObject { param([string]$Message,[string]$Type) return [pscustomobject]@{ error = [pscustomobject]@{ message = $Message; type = $Type } } }
function Write-JsonResponse { param($Context,[int]$StatusCode,$Object) $r = $Context.Response; Set-CommonApiHeaders -Response $r; $r.StatusCode = $StatusCode; $r.ContentType = "application/json"; $b = [Text.Encoding]::UTF8.GetBytes((ConvertTo-CompactJson -Value $Object)); $r.ContentLength64 = $b.Length; $r.OutputStream.Write($b,0,$b.Length); $r.OutputStream.Close() }
function Write-EmptyResponse { param($Context,[int]$StatusCode) $r = $Context.Response; Set-CommonApiHeaders -Response $r; $r.StatusCode = $StatusCode; $r.ContentLength64 = 0; $r.OutputStream.Close() }
function Read-RequestBodyText { param($Request) $reader = [IO.StreamReader]::new($Request.InputStream, $Request.ContentEncoding); try { return $reader.ReadToEnd() } finally { $reader.Dispose() } }
function Test-ApiAuthorization { param($Request,[string]$ExpectedKey) $header = [string]$Request.Headers["Authorization"]; return ($header -match '^Bearer\s+(.+)$' -and $matches[1] -eq $ExpectedKey) }
function Write-UnauthorizedResponse { param($Context) Write-JsonResponse -Context $Context -StatusCode 401 -Object (New-ApiErrorObject -Message "Unauthorized" -Type "invalid_api_key") }

function Convert-AnonymousModelsToOpenAi {
    param($Models)
    return [pscustomobject]@{
        object = "list"
        data = @($Models.models | ForEach-Object { [pscustomobject]@{ id = [string]$_.slug; object = "model"; created = 0; owned_by = "openai"; root = [string]$_.slug; parent = $null } })
    }
}

function New-ChatCompletionId { return "chatcmpl_$([guid]::NewGuid().ToString('N'))" }

function Invoke-ChatCompletion {
    param($GlobalState, $Request, $Body)
    if (-not $Body.PSObject.Properties["messages"] -or -not $Body.messages) { throw "messages is required" }
    $messages = @($Body.messages)
    $model = if ($Body.PSObject.Properties["model"] -and $Body.model) { [string]$Body.model } else { [string]$GlobalState.model }
    $tools = if ($Body.PSObject.Properties["tools"] -and $Body.tools) { @(Convert-ToObjectArray -Value $Body.tools | Where-Object { $null -ne $_ }) } else { @() }
    $toolChoice = if ($Body.PSObject.Properties["tool_choice"]) { $Body.tool_choice } else { $null }
    $stream = ($Body.PSObject.Properties["stream"] -and $Body.stream)
    $sessionKey = Get-SessionKeyFromRequest -Request $Request -Body $Body
    $store = Load-ApiSessions
    $session = if ($sessionKey) { Get-ApiSession -Store $store -Key $sessionKey } else { $null }
    if (-not $session -and $sessionKey) {
        $session = [pscustomobject]@{ key = $sessionKey; conversation_id = $null; parent_message_id = $null; last_assistant_message_id = $null; model = $model; last_tools = @(); history_fingerprints = @(); updated_at = $null }
    }
    $state = New-ConversationStateFrom -State $GlobalState -Model $model
    if ($session) {
        $state.conversation_id = $session.conversation_id
        $state.parent_message_id = $session.parent_message_id
        $state.last_assistant_message_id = $session.last_assistant_message_id
        $state.last_tools = if ($session.last_tools) { @($session.last_tools) } else { @() }
    }
    $promptInfo = Get-SessionPromptMessages -Session $session -Messages $messages
    $result = Invoke-AnonymousConversation -State $state -Prompt (Convert-MessagesToPrompt -Messages $promptInfo.prompt_messages -Model $model -Tools $tools -ToolChoice $toolChoice)
    if ($session) {
        $session.conversation_id = $result.conversation_id
        $session.parent_message_id = $result.parent_message_id
        $session.last_assistant_message_id = $result.last_assistant_message_id
        $session.model = $model
        $session.last_tools = if ($result.last_tools) { @($result.last_tools) } else { @() }
        $session.history_fingerprints = $promptInfo.history_fingerprints
        $session.updated_at = (Get-Date).ToUniversalTime().ToString("o")
        Save-ApiSessionRecord -Store $store -Session $session
    }
    $parsed = if (@($tools).Count -gt 0 -and $toolChoice -ne "none") { Try-ParseToolEnvelope -Text $result.assistant_text } else { $null }
    if ($parsed -and @(Convert-ToObjectArray -Value $parsed.tool_calls).Count -gt 0) {
        return [pscustomobject]@{ stream = [bool]$stream; model = $model; assistant_text = $null; tool_calls = @($parsed.tool_calls); finish_reason = "tool_calls" }
    }
    return [pscustomobject]@{ stream = [bool]$stream; model = $model; assistant_text = $(if ($parsed -and $parsed.assistant_text -ne $null) { [string]$parsed.assistant_text } else { [string]$result.assistant_text }); tool_calls = @(); finish_reason = "stop" }
}

function Write-SseData { param($Response,$Object) $bytes = [Text.Encoding]::UTF8.GetBytes("data: $(ConvertTo-CompactJson -Value $Object)`n`n"); $Response.OutputStream.Write($bytes,0,$bytes.Length); $Response.OutputStream.Flush() }
function Write-SseDone { param($Response) $bytes = [Text.Encoding]::UTF8.GetBytes("data: [DONE]`n`n"); $Response.OutputStream.Write($bytes,0,$bytes.Length); $Response.OutputStream.Flush() }

function Write-ChatCompletionStream {
    param($Response,[string]$CompletionId,[string]$Model,[datetimeoffset]$CreatedAt,[string]$AssistantText,$ToolCalls,[string]$FinishReason)
    $created = [int]$CreatedAt.ToUnixTimeSeconds()
    if ($ToolCalls -and @($ToolCalls).Count -gt 0) {
        $calls = @()
        for ($i = 0; $i -lt @($ToolCalls).Count; $i++) {
            $calls += [pscustomobject]@{ index = $i; id = $ToolCalls[$i].id; type = "function"; function = [pscustomobject]@{ name = $ToolCalls[$i].function.name; arguments = $ToolCalls[$i].function.arguments } }
        }
        Write-SseData -Response $Response -Object ([pscustomobject]@{ id = $CompletionId; object = "chat.completion.chunk"; created = $created; model = $Model; choices = @([pscustomobject]@{ index = 0; delta = [pscustomobject]@{ role = "assistant"; tool_calls = $calls }; finish_reason = $null }) })
        Write-SseData -Response $Response -Object ([pscustomobject]@{ id = $CompletionId; object = "chat.completion.chunk"; created = $created; model = $Model; choices = @([pscustomobject]@{ index = 0; delta = [pscustomobject]@{}; finish_reason = $FinishReason }) })
        Write-SseDone -Response $Response
        return
    }
    $chunks = @()
    if (-not [string]::IsNullOrEmpty($AssistantText)) {
        for ($i = 0; $i -lt $AssistantText.Length; $i += 80) { $chunks += $AssistantText.Substring($i, [Math]::Min(80, $AssistantText.Length - $i)) }
    }
    if (@($chunks).Count -eq 0) { $chunks = @("") }
    $first = $true
    foreach ($chunk in $chunks) {
        $delta = [ordered]@{}
        if ($first) { $delta.role = "assistant" }
        $delta.content = $chunk
        Write-SseData -Response $Response -Object ([pscustomobject]@{ id = $CompletionId; object = "chat.completion.chunk"; created = $created; model = $Model; choices = @([pscustomobject]@{ index = 0; delta = [pscustomobject]$delta; finish_reason = $null }) })
        $first = $false
    }
    Write-SseData -Response $Response -Object ([pscustomobject]@{ id = $CompletionId; object = "chat.completion.chunk"; created = $created; model = $Model; choices = @([pscustomobject]@{ index = 0; delta = [pscustomobject]@{}; finish_reason = $FinishReason }) })
    Write-SseDone -Response $Response
}

function Handle-ApiContext {
    param($Context, $ServerConfig)
    $request = $Context.Request
    $path = [string]$request.Url.AbsolutePath
    $method = [string]$request.HttpMethod
    if ($method -eq "OPTIONS") { Write-EmptyResponse -Context $Context -StatusCode 204; return }
    if ($path -eq "/__shutdown" -and $method -eq "POST") {
        $key = [string]$request.QueryString["key"]
        if ($key -eq [string]$ServerConfig.api_key) {
            $script:StopLocalApiServer = $true
            Write-EmptyResponse -Context $Context -StatusCode 204
            return
        }
        Write-JsonResponse -Context $Context -StatusCode 401 -Object (New-ApiErrorObject -Message "Unauthorized" -Type "invalid_api_key")
        return
    }
    if ($path -eq "/health" -and $method -eq "GET") {
        $state = Load-State
        Write-JsonResponse -Context $Context -StatusCode 200 -Object ([pscustomobject]@{ object = "health"; status = "ok"; port = [int]$ServerConfig.port; api_base = "http://127.0.0.1:$([int]$ServerConfig.port)/v1"; default_model = [string]$state.model; model_cache_age_seconds = (Get-ModelsCacheAgeSeconds); default_session_mode = [string]$ServerConfig.default_session_mode })
        return
    }
    if (-not (Test-ApiAuthorization -Request $request -ExpectedKey ([string]$ServerConfig.api_key))) { Write-UnauthorizedResponse -Context $Context; return }
    if ($path -eq "/v1/models" -and $method -eq "GET") { Write-JsonResponse -Context $Context -StatusCode 200 -Object (Convert-AnonymousModelsToOpenAi -Models (Get-Models -State (Load-State) -PreferCache)); return }
    if ($path -eq "/v1/chat/completions" -and $method -eq "POST") {
        $bodyText = Read-RequestBodyText -Request $request
        if ([string]::IsNullOrWhiteSpace($bodyText)) { Write-JsonResponse -Context $Context -StatusCode 400 -Object (New-ApiErrorObject -Message "Request body is required" -Type "invalid_request_error"); return }
        try { $body = $bodyText | ConvertFrom-Json } catch { Write-JsonResponse -Context $Context -StatusCode 400 -Object (New-ApiErrorObject -Message "Invalid JSON body" -Type "invalid_request_error"); return }
        try { $completion = Invoke-ChatCompletion -GlobalState (Load-State) -Request $request -Body $body } catch { Write-JsonResponse -Context $Context -StatusCode 400 -Object (New-ApiErrorObject -Message $_.Exception.Message -Type "invalid_request_error"); return }
        $id = New-ChatCompletionId
        $created = [datetimeoffset]::UtcNow
        if ($completion.stream) {
            $response = $Context.Response
            Set-CommonApiHeaders -Response $response
            $response.StatusCode = 200
            $response.SendChunked = $true
            $response.ContentType = "text/event-stream"
            Write-ChatCompletionStream -Response $response -CompletionId $id -Model ([string]$completion.model) -CreatedAt $created -AssistantText ([string]$completion.assistant_text) -ToolCalls $completion.tool_calls -FinishReason ([string]$completion.finish_reason)
            $response.OutputStream.Close()
            return
        }
        $message = if ($completion.tool_calls -and @($completion.tool_calls).Count -gt 0) { [pscustomobject]@{ role = "assistant"; content = $null; tool_calls = @($completion.tool_calls) } } else { [pscustomobject]@{ role = "assistant"; content = [string]$completion.assistant_text } }
        Write-JsonResponse -Context $Context -StatusCode 200 -Object ([pscustomobject]@{ id = $id; object = "chat.completion"; created = [int]$created.ToUnixTimeSeconds(); model = [string]$completion.model; choices = @([pscustomobject]@{ index = 0; message = $message; finish_reason = [string]$completion.finish_reason }); usage = [pscustomobject]@{ prompt_tokens = 0; completion_tokens = 0; total_tokens = 0 } })
        return
    }
    Write-JsonResponse -Context $Context -StatusCode 404 -Object (New-ApiErrorObject -Message "Not found" -Type "invalid_request_error")
}

function Start-LocalApiServer {
    param($ServerConfig)
    $listener = [Net.HttpListener]::new()
    $listener.Prefixes.Add("http://127.0.0.1:$([int]$ServerConfig.port)/")
    $listener.Start()
    $script:StopLocalApiServer = $false
    try {
        while ($listener.IsListening -and -not $script:StopLocalApiServer) {
            try { $context = $listener.GetContext() } catch { if ($listener.IsListening) { throw } else { break } }
            try { Handle-ApiContext -Context $context -ServerConfig $ServerConfig } catch { try { Write-JsonResponse -Context $context -StatusCode 500 -Object (New-ApiErrorObject -Message $_.Exception.Message -Type "server_error") } catch {} }
        }
    }
    finally {
        if ($listener.IsListening) { $listener.Stop() }
        $listener.Close()
    }
}

function Start-EmbeddedServerRunspace {
    param($ServerConfig)
    $ps = [powershell]::Create()
    [void]$ps.AddCommand($TerminalScriptPath)
    [void]$ps.AddParameter("ServeOnly")
    [void]$ps.AddParameter("Port", [int]$ServerConfig.port)
    [void]$ps.AddParameter("ApiKey", [string]$ServerConfig.api_key)
    $async = $ps.BeginInvoke()
    Start-Sleep -Milliseconds 400
    if ($ps.Streams.Error.Count -gt 0) {
        $text = ($ps.Streams.Error | Out-String).Trim()
        try { $ps.Stop() } catch {}
        $ps.Dispose()
        throw "local server failed: $text"
    }
    return [pscustomobject]@{ power_shell = $ps; async_result = $async; port = [int]$ServerConfig.port; api_key = [string]$ServerConfig.api_key }
}

function Stop-LocalApiServerByPortAndKey {
    param(
        [int]$Port,
        [string]$ApiKey
    )
    if ($Port -le 0 -or [string]::IsNullOrWhiteSpace($ApiKey)) {
        return
    }
    $uri = "http://127.0.0.1:$Port/__shutdown?key=$([uri]::EscapeDataString($ApiKey))"
    $request = [Net.WebRequest]::Create($uri)
    $request.Method = "POST"
    $request.Timeout = 1500
    $request.ReadWriteTimeout = 1500
    $request.ContentLength = 0
    $response = $request.GetResponse()
    $response.Close()
}

function Test-LocalApiServerAlive {
    param([int]$Port)
    if ($Port -le 0) {
        return $false
    }
    try {
        $uri = "http://127.0.0.1:$Port/health"
        $request = [Net.WebRequest]::Create($uri)
        $request.Method = "GET"
        $request.Timeout = 1500
        $request.ReadWriteTimeout = 1500
        $response = $request.GetResponse()
        $response.Close()
        return $true
    }
    catch {
        return $false
    }
}

function Stop-EmbeddedServerRunspace {
    param($Handle)
    if (-not $Handle) { return }
    try {
        Stop-LocalApiServerByPortAndKey -Port ([int]$Handle.port) -ApiKey ([string]$Handle.api_key)
    }
    catch {}
    try { $Handle.power_shell.EndInvoke($Handle.async_result) } catch {}
    finally { $Handle.power_shell.Dispose() }
}

if ($Stop) {
    Stop-RunningTerminal
    return
}

$state = Load-State
$serverConfig = Load-ServerConfig -PortOverride $Port -ApiKeyOverride $ApiKey
Sync-ModelTools -State $state

if ($ServeOnly) {
    Save-TerminalInfo -ServerConfig $serverConfig
    try {
        Start-LocalApiServer -ServerConfig $serverConfig
    }
    finally {
        Remove-TerminalInfo
    }
    return
}

if ($NoLoop) {
    return
}

$serverHandle = $null
if (-not $NoServer -and $serverConfig.autostart_server) {
    try {
        $serverHandle = Start-EmbeddedServerRunspace -ServerConfig $serverConfig
        Write-Host "api_base=http://127.0.0.1:$([int]$serverConfig.port)/v1"
        Write-Host "api_key=$([string]$serverConfig.api_key)"
    }
    catch {
        Write-Host "api_error=$($_.Exception.Message)"
    }
}

Save-TerminalInfo -ServerConfig $serverConfig

Write-Host "openai-unlimited terminal"
Write-Host "model=$($state.model)"
if ($state.last_tools -and @($state.last_tools).Count -gt 0) {
    Write-Host "active_tools=$(@($state.last_tools) -join ',')"
}
Write-Host "device_id=$($state.device_id)"
Write-Host "type /help"

$queuedCommands = @()
if ($ScriptLine) {
    $queuedCommands = @($ScriptLine)
}

try {
    while ($true) {
        $shouldExit = $false
        if ($queuedCommands.Count -gt 0) {
            $line = [string]$queuedCommands[0]
            if ($queuedCommands.Count -eq 1) {
                $queuedCommands = @()
            }
            else {
                $queuedCommands = @($queuedCommands[1..($queuedCommands.Count - 1)])
            }
            Write-Host "openai-unlimited: $line"
        }
        else {
            $line = Read-Host "openai-unlimited"
        }
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        if ($line.StartsWith("/")) {
            $parts = @($line.Split(" ", 2, [System.StringSplitOptions]::RemoveEmptyEntries))
            $cmd = $parts[0].ToLowerInvariant()
            try {
                switch ($cmd) {
                    "/help" { Show-Help }
                    "/models" { Show-Models -Models (Get-Models -State $state -PreferCache) }
                    "/categories" { Show-Categories -Models (Get-Models -State $state -PreferCache) }
                    "/model" {
                        if ($parts.Count -lt 2) { throw "missing slug" }
                        Set-Model -State $state -Slug $parts[1].Trim()
                    }
                    "/state" { Show-State -State $state }
                    "/new" { Reset-Conversation -State $state }
                    "/device-reset" { Reset-Device -State $state }
                    "/exit" { $shouldExit = $true }
                    default { Write-Host "unknown command" }
                }
            }
            catch {
                Write-Host "error=$($_.Exception.Message)"
            }
            if ($shouldExit) {
                break
            }
            continue
        }

        try {
            Send-Conversation -State $state -Prompt $line
        }
        catch {
            Write-Host "error=$($_.Exception.Message)"
        }
    }
}
finally {
    Stop-EmbeddedServerRunspace -Handle $serverHandle
    $serverStillRunning = $false
    if (-not $NoServer -and $serverConfig -and $serverConfig.autostart_server) {
        $serverStillRunning = Test-LocalApiServerAlive -Port ([int]$serverConfig.port)
    }
    if (-not $serverStillRunning) {
        Remove-TerminalInfo
    }
}
