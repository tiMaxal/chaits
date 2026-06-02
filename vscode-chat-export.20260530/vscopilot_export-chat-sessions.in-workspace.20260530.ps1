param(
    [string]$WorkspacePath = (Get-Location).Path,
    [string]$OutputDir = "",
    [string[]]$AdditionalMarkers = @(),
    [switch]$IncludeGlobalEmptyWindow = $true,
    [switch]$IncludeRawJson,
    [switch]$CleanOutput
)

$ErrorActionPreference = 'Stop'

function Get-StringValue {
    param($Object)
    if ($null -eq $Object) { return '' }
    if ($Object -is [string]) { return $Object }
    if ($Object.PSObject.Properties.Name -contains 'value') { return [string]$Object.value }
    return [string]$Object
}

function To-DateTimeOrNull {
    param($Value)
    if ($null -eq $Value) { return $null }

    try {
        if ($Value -is [long] -or $Value -is [int] -or $Value -is [double]) {
            return [DateTimeOffset]::FromUnixTimeMilliseconds([long]$Value).DateTime
        }

        $text = [string]$Value
        if ([string]::IsNullOrWhiteSpace($text)) { return $null }
        return [datetime]::Parse($text)
    }
    catch {
        return $null
    }
}

function Sanitize-Name {
    param([string]$Name)
    if ([string]::IsNullOrWhiteSpace($Name)) { return 'untitled-chat' }

    $bad = [System.IO.Path]::GetInvalidFileNameChars() -join ''
    $pattern = '[' + [regex]::Escape($bad) + ']'
    $clean = ($Name -replace $pattern, ' ')
    $clean = ($clean -replace '\s+', ' ').Trim()
    $clean = ($clean -replace '[^\w\s\-]', ' ')
    $clean = ($clean -replace '\s+', ' ').Trim()
    if ($clean.Length -gt 90) { $clean = $clean.Substring(0, 90).Trim() }
    if ([string]::IsNullOrWhiteSpace($clean)) { return 'untitled-chat' }
    return $clean
}

function Sanitize-FolderName {
    param([string]$Name)
    if ([string]::IsNullOrWhiteSpace($Name)) { return 'workspace' }

    $bad = [System.IO.Path]::GetInvalidFileNameChars() -join ''
    $pattern = '[' + [regex]::Escape($bad) + ']'
    $clean = ($Name -replace $pattern, '-')
    $clean = ($clean -replace '\s+', '-')
    $clean = ($clean -replace '-{2,}', '-')
    $clean = $clean.Trim('-')
    if ([string]::IsNullOrWhiteSpace($clean)) { return 'workspace' }
    return $clean
}

function New-Entry {
    param(
        [Nullable[datetime]]$Timestamp,
        [string]$Role,
        [string]$Category,
        [string]$Text
    )
    if ([string]::IsNullOrWhiteSpace($Text)) { return $null }
    return [pscustomobject]@{
        Timestamp = $Timestamp
        Role = $Role
        Category = $Category
        Text = $Text.Trim()
    }
}

function Parse-Transcript {
    param([string]$FilePath)

    $lines = Get-Content -Path $FilePath
    $sessionId = [System.IO.Path]::GetFileNameWithoutExtension($FilePath)
    $title = $null
    $start = $null
    $entries = [System.Collections.Generic.List[object]]::new()

    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $obj = $null
        try { $obj = $line | ConvertFrom-Json } catch { continue }

        $ts = To-DateTimeOrNull $obj.timestamp
        if ($null -eq $start -and $ts) { $start = $ts }

        switch ($obj.type) {
            'session.start' {
                if ($obj.data.sessionId) { $sessionId = [string]$obj.data.sessionId }
                $startTs = To-DateTimeOrNull $obj.data.startTime
                if ($startTs) { $start = $startTs }
            }
            'user.message' {
                $text = [string]$obj.data.content
                if (-not $title -and -not [string]::IsNullOrWhiteSpace($text)) {
                    $preview = ($text -replace '\s+', ' ').Trim()
                    if ($preview.Length -gt 80) { $preview = $preview.Substring(0, 80).Trim() + '...' }
                    $title = $preview
                }
                $e = New-Entry -Timestamp $ts -Role 'USER' -Category 'message' -Text $text
                if ($e) { $entries.Add($e) | Out-Null }
            }
            'assistant.message' {
                $text = [string]$obj.data.content
                $e = New-Entry -Timestamp $ts -Role 'ASSISTANT' -Category 'message' -Text $text
                if ($e) { $entries.Add($e) | Out-Null }

                if ($obj.data.toolRequests) {
                    foreach ($toolReq in $obj.data.toolRequests) {
                        $toolText = "Tool request: $($toolReq.name)" 
                        if ($toolReq.arguments) {
                            $toolText += "`nArguments: $($toolReq.arguments)"
                        }
                        $te = New-Entry -Timestamp $ts -Role 'TOOL' -Category 'request' -Text $toolText
                        if ($te) { $entries.Add($te) | Out-Null }
                    }
                }
            }
            'tool.execution_start' {
                $name = [string]$obj.data.toolName
                $args = $obj.data.arguments | ConvertTo-Json -Depth 20 -Compress
                $te = New-Entry -Timestamp $ts -Role 'TOOL' -Category 'execution-start' -Text ("$name started`nArguments: $args")
                if ($te) { $entries.Add($te) | Out-Null }
            }
            'tool.execution_complete' {
                $name = [string]$obj.data.toolCallId
                $ok = [string]$obj.data.success
                $te = New-Entry -Timestamp $ts -Role 'TOOL' -Category 'execution-complete' -Text ("$name completed; success=$ok")
                if ($te) { $entries.Add($te) | Out-Null }
            }
        }
    }

    if (-not $title) { $title = "Chat $sessionId" }

    return [pscustomobject]@{
        SessionId = $sessionId
        Title = $title
        Start = $start
        Entries = $entries
        Format = 'transcript'
    }
}

function Parse-ChatSession {
    param([string]$FilePath)

    $lines = Get-Content -Path $FilePath
    $sessionId = [System.IO.Path]::GetFileNameWithoutExtension($FilePath)
    $title = $null
    $start = $null
    $currentInput = ''
    $entries = [System.Collections.Generic.List[object]]::new()
    $seenRequests = [System.Collections.Generic.HashSet[string]]::new()

    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $obj = $null
        try { $obj = $line | ConvertFrom-Json } catch { continue }

        if ($obj.kind -eq 0) {
            if ($obj.v.sessionId) { $sessionId = [string]$obj.v.sessionId }
            $ts = To-DateTimeOrNull $obj.v.creationDate
            if ($ts) { $start = $ts }
            continue
        }

        if ($obj.kind -eq 1) {
            if ($obj.k -and $obj.k.Count -ge 1) {
                if ($obj.k[$obj.k.Count - 1] -eq 'customTitle') {
                    $title = [string]$obj.v
                }
                if ($obj.k[$obj.k.Count - 1] -eq 'inputText') {
                    $currentInput = [string]$obj.v
                }
            }
            continue
        }

        if ($obj.kind -ne 2) { continue }
        if (-not $obj.k -or $obj.k.Count -eq 0) { continue }
        if ($obj.k[0] -ne 'requests') { continue }
        if (-not ($obj.v -is [System.Collections.IEnumerable])) { continue }

        foreach ($req in $obj.v) {
            if (-not $req) { continue }
            $requestId = [string]$req.requestId
            if ([string]::IsNullOrWhiteSpace($requestId)) { continue }
            if ($seenRequests.Contains($requestId)) { continue }
            [void]$seenRequests.Add($requestId)

            $rts = To-DateTimeOrNull $req.timestamp
            if ($null -eq $start -and $rts) { $start = $rts }

            if (-not [string]::IsNullOrWhiteSpace($currentInput)) {
                if (-not $title) {
                    $preview = ($currentInput -replace '\s+', ' ').Trim()
                    if ($preview.Length -gt 80) { $preview = $preview.Substring(0, 80).Trim() + '...' }
                    $title = $preview
                }
                $ue = New-Entry -Timestamp $rts -Role 'USER' -Category 'message' -Text $currentInput
                if ($ue) { $entries.Add($ue) | Out-Null }
            }

            if ($req.response -and ($req.response -is [System.Collections.IEnumerable])) {
                foreach ($chunk in $req.response) {
                    if (-not $chunk) { continue }

                    if ($chunk.kind -eq 'toolInvocationSerialized') {
                        $inv = Get-StringValue $chunk.invocationMessage
                        $past = Get-StringValue $chunk.pastTenseMessage
                        $combined = if (-not [string]::IsNullOrWhiteSpace($past)) { "$inv`n$past" } else { $inv }
                        $te = New-Entry -Timestamp $rts -Role 'TOOL' -Category 'activity' -Text $combined
                        if ($te) { $entries.Add($te) | Out-Null }
                        continue
                    }

                    if ($chunk.kind -eq 'textEditGroup') {
                        $count = 0
                        if ($chunk.edits) {
                            foreach ($group in $chunk.edits) {
                                if ($group) { $count += $group.Count }
                            }
                        }
                        $ce = New-Entry -Timestamp $rts -Role 'CODE' -Category 'workspace-edit' -Text ("Workspace edit applied ($count edits).")
                        if ($ce) { $entries.Add($ce) | Out-Null }
                        continue
                    }

                    $val = Get-StringValue $chunk.value
                    if (-not [string]::IsNullOrWhiteSpace($val)) {
                        $ae = New-Entry -Timestamp $rts -Role 'ASSISTANT' -Category 'message' -Text $val
                        if ($ae) { $entries.Add($ae) | Out-Null }
                    }
                }
            }

            if ($req.result -and $req.result.metadata -and $req.result.metadata.codeBlocks) {
                foreach ($cb in $req.result.metadata.codeBlocks) {
                    if (-not $cb.code) { continue }
                    $lang = [string]$cb.language
                    if ([string]::IsNullOrWhiteSpace($lang)) { $lang = 'text' }
                    $fence = ('`' * 3)
                    $codeText = $fence + $lang + "`n" + $cb.code.TrimEnd() + "`n" + $fence
                    $ce = New-Entry -Timestamp $rts -Role 'CODE' -Category 'code-block' -Text $codeText
                    if ($ce) { $entries.Add($ce) | Out-Null }
                }
            }
        }
    }

    if (-not $title) { $title = "Chat $sessionId" }

    return [pscustomobject]@{
        SessionId = $sessionId
        Title = $title
        Start = $start
        Entries = $entries
        Format = 'chatSession'
    }
}

function Score-Source {
    param([string]$Path)
    if ($Path -match 'GitHub\.copilot-chat\\transcripts') { return 3 }
    if ($Path -match '\\chatSessions\\') { return 2 }
    if ($Path -match 'emptyWindowChatSessions') { return 1 }
    return 0
}

$workspaceFull = [System.IO.Path]::GetFullPath($WorkspacePath)
$workspaceLeaf = Split-Path -Leaf $workspaceFull
$workspaceParentLeaf = Split-Path -Leaf (Split-Path -Parent $workspaceFull)

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $workspaceFolderName = Sanitize-FolderName $workspaceLeaf
    $OutputDir = Join-Path $PSScriptRoot ("$workspaceFolderName-chats")
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

if ($CleanOutput) {
    Get-ChildItem -Path $OutputDir -File -Filter '*.md' -ErrorAction SilentlyContinue | Remove-Item -Force
}

$markers = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
[void]$markers.Add($workspaceFull)
[void]$markers.Add($workspaceLeaf)
if (-not [string]::IsNullOrWhiteSpace($workspaceParentLeaf)) { [void]$markers.Add($workspaceParentLeaf) }
foreach ($m in $AdditionalMarkers) {
    if (-not [string]::IsNullOrWhiteSpace($m)) { [void]$markers.Add($m) }
}

$userRoot = Join-Path $env:APPDATA 'Code\User'
$candidates = [System.Collections.Generic.List[object]]::new()
$allowedWorkspaceRoots = [System.Collections.Generic.List[string]]::new()
$workspaceCodeFile = Join-Path (Split-Path -Parent $PSScriptRoot) ($workspaceLeaf + '.code-workspace')

$workspaceStorageRoot = Join-Path $userRoot 'workspaceStorage'
if (Test-Path $workspaceStorageRoot) {
    foreach ($storageDir in (Get-ChildItem -Path $workspaceStorageRoot -Directory -ErrorAction SilentlyContinue)) {
        $metaPath = Join-Path $storageDir.FullName 'workspace.json'
        if (-not (Test-Path $metaPath)) { continue }

        $meta = $null
        try {
            $meta = Get-Content -Path $metaPath -Raw | ConvertFrom-Json
        } catch {
            continue
        }

        $workspaceUri = $null
        if ($meta.workspace) { $workspaceUri = [string]$meta.workspace }
        elseif ($meta.folder) { $workspaceUri = [string]$meta.folder }
        if ([string]::IsNullOrWhiteSpace($workspaceUri)) { continue }

        $localPath = $null
        try {
            $localPath = ([Uri]$workspaceUri).LocalPath
        } catch {
            $localPath = [System.Uri]::UnescapeDataString($workspaceUri)
        }

        if ([string]::IsNullOrWhiteSpace($localPath)) { continue }

        if ($localPath -match '^/[A-Za-z]:/') {
            $localPath = $localPath.Substring(1)
        }

        $resolvedPath = [System.IO.Path]::GetFullPath($localPath)
        if ($resolvedPath -ieq $workspaceFull -or $resolvedPath -ieq $workspaceCodeFile) {
            $allowedWorkspaceRoots.Add($storageDir.FullName) | Out-Null
            $files = Get-ChildItem -Path $storageDir.FullName -Recurse -File -Filter '*.jsonl' -ErrorAction SilentlyContinue |
                Where-Object { $_.FullName -match 'GitHub\.copilot-chat\\transcripts\\' }
            foreach ($f in $files) {
                $candidates.Add($f) | Out-Null
            }
        }
    }
}

if ($IncludeGlobalEmptyWindow) {
    $globalRoot = Join-Path $userRoot 'globalStorage\emptyWindowChatSessions'
    if (Test-Path $globalRoot) {
        foreach ($f in (Get-ChildItem -Path $globalRoot -File -Filter '*.jsonl' -ErrorAction SilentlyContinue)) {
            $candidates.Add($f) | Out-Null
        }
    }
}

$markerPattern = ($markers | ForEach-Object { [regex]::Escape($_) }) -join '|'

$selected = [System.Collections.Generic.Dictionary[string, object]]::new()

foreach ($f in $candidates) {
    $raw = Get-Content -Path $f.FullName -Raw -ErrorAction SilentlyContinue
    if ([string]::IsNullOrWhiteSpace($raw)) { continue }
    if (-not [string]::IsNullOrWhiteSpace($markerPattern) -and $raw -notmatch $markerPattern) { continue }

    $key = [System.IO.Path]::GetFileNameWithoutExtension($f.Name)
    $score = Score-Source $f.FullName
    $candidate = [pscustomobject]@{
        Key = $key
        Path = $f.FullName
        Score = $score
        Length = $f.Length
        Raw = $raw
    }

    if (-not $selected.ContainsKey($key)) {
        $selected[$key] = $candidate
        continue
    }

    $existing = $selected[$key]
    if ($candidate.Score -gt $existing.Score -or ($candidate.Score -eq $existing.Score -and $candidate.Length -gt $existing.Length)) {
        $selected[$key] = $candidate
    }
}

$exports = [System.Collections.Generic.List[object]]::new()

foreach ($item in ($selected.Values | Sort-Object Key)) {
    $isTranscript = ($item.Path -match 'GitHub\.copilot-chat\\transcripts\\')

    $parsed = if ($isTranscript) { Parse-Transcript -FilePath $item.Path } else { Parse-ChatSession -FilePath $item.Path }
    if (-not $parsed.Entries -or $parsed.Entries.Count -eq 0) { continue }

    $title = Sanitize-Name $parsed.Title
    $datePrefix = 'undated'
    if ($parsed.Start) { $datePrefix = $parsed.Start.ToString('yyyy-MM-dd') }

    $baseFile = "$datePrefix - $title"
    $fileName = "$baseFile.md"
    $outPath = Join-Path $OutputDir $fileName

    if (Test-Path $outPath) {
        $fileName = "$baseFile [$($parsed.SessionId.Substring(0,8))].md"
        $outPath = Join-Path $OutputDir $fileName
    }

    $orderedEntries = $parsed.Entries | Sort-Object @{ Expression = { if ($_.Timestamp) { $_.Timestamp } else { [datetime]::MaxValue } } }

    $md = [System.Collections.Generic.List[string]]::new()
    $md.Add("# $datePrefix - $($parsed.Title)") | Out-Null
    $md.Add('') | Out-Null
    $md.Add("- Session ID: $($parsed.SessionId)") | Out-Null
    $md.Add("- Source file: $($item.Path)") | Out-Null
    $md.Add("- Source format: $($parsed.Format)") | Out-Null
    $md.Add("- Activity entries: $($orderedEntries.Count)") | Out-Null
    $md.Add('') | Out-Null
    $md.Add('## Timeline') | Out-Null
    $md.Add('') | Out-Null

    foreach ($e in $orderedEntries) {
        $ts = if ($e.Timestamp) { $e.Timestamp.ToString('yyyy-MM-dd HH:mm:ss') } else { 'unknown-time' }
        $md.Add("### [$ts] $($e.Role) ($($e.Category))") | Out-Null
        $md.Add('') | Out-Null
        $md.Add($e.Text) | Out-Null
        $md.Add('') | Out-Null
    }

    if ($IncludeRawJson) {
        $md.Add('## Raw Source JSONL') | Out-Null
        $md.Add('') | Out-Null
        $md.Add('```jsonl') | Out-Null
        $md.Add($item.Raw.TrimEnd()) | Out-Null
        $md.Add('```') | Out-Null
        $md.Add('') | Out-Null
    }

    ($md -join "`r`n") | Out-File -LiteralPath $outPath -Encoding utf8 -Force

    $exports.Add([pscustomobject]@{
        SessionId = $parsed.SessionId
        Start = $parsed.Start
        Title = $parsed.Title
        File = $fileName
        Source = $item.Path
        EntryCount = $orderedEntries.Count
    }) | Out-Null
}

$index = [System.Collections.Generic.List[string]]::new()
$index.Add('# Chat Export Index') | Out-Null
$index.Add('') | Out-Null
$index.Add("Workspace marker: $workspaceFull") | Out-Null
$index.Add("Generated at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')") | Out-Null
$index.Add('') | Out-Null

foreach ($x in ($exports | Sort-Object @{ Expression = { if ($_.Start) { $_.Start } else { [datetime]::MaxValue } } }, Title)) {
    $date = if ($x.Start) { $x.Start.ToString('yyyy-MM-dd') } else { 'undated' }
    $index.Add("- $date | $($x.Title)") | Out-Null
    $index.Add("  - File: $($x.File)") | Out-Null
    $index.Add("  - Session: $($x.SessionId)") | Out-Null
    $index.Add("  - Entries: $($x.EntryCount)") | Out-Null
}

$index.Add('') | Out-Null
$index.Add("Total chats exported: $($exports.Count)") | Out-Null

($index -join "`r`n") | Out-File -LiteralPath (Join-Path $OutputDir 'INDEX.md') -Encoding utf8 -Force

Write-Host "Exported $($exports.Count) chat(s) to $OutputDir"
