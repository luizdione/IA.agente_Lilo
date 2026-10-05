# LILO v14 - operacao (o icone da Area de Trabalho aponta p/ ca).
#
#   .\lilo.ps1                      abre a interface (sobe o que faltar)
#   .\lilo.ps1 up                   sobe a interface e aquece o modelo
#   .\lilo.ps1 down                 para a interface e descarrega o modelo
#   .\lilo.ps1 status               interruptor, modelos na GPU, VRAM, interface
#   .\lilo.ps1 warm                 poe o modelo na GPU (leitura previa + 1 geracao)
#   .\lilo.ps1 bench [...]          mede o tempo ate o 1o token (scripts\bench.py)
#   .\lilo.ps1 gpu-livre [motivo]   reserva a GPU p/ MD, Boltz ou render
#   .\lilo.ps1 gpu-ok [forcar]      devolve a GPU ao LILO e aquece
#
# Compativel com Windows PowerShell 5.1 (o atalho usa powershell.exe): so ASCII.
param(
    [Parameter(Position = 0)][string]$Comando = "abrir",
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Resto
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$Raiz    = $PSScriptRoot
$Compose = Join-Path $Raiz "compose.yaml"
$Py      = if ($env:LILO_PY) { $env:LILO_PY } else { "C:\Users\luizd\miniforge3\envs\datascience\python.exe" }
$Ollama  = "http://127.0.0.1:11434"
$WebUI   = "http://127.0.0.1:3000"
$Modelo  = "lilo"
$LogDir  = Join-Path $env:LOCALAPPDATA "LILO\bench"
$ArqInterruptor = Join-Path $env:USERPROFILE ".ollama_delegate\switch.json"
# VRAM livre (MiB) exigida para carregar o modelo: qwen3:14b a 8k ocupa ~9,2-9,8 GB.
# Abaixo disso ha outro job na GPU e o modelo derramaria para a CPU, disputando VRAM.
$VramMinima = 9800

# ---------------------------------------------------------------- interruptor
# Mesmo arquivo do MCP ollama-local: um interruptor so para toda a GPU.
# A variavel NAO pode se chamar $Switch: dentro de um bloco `switch` o PowerShell
# a troca pelo enumerador do bloco, a leitura falha e o interruptor parece ligado.
function Get-Interruptor {
    # Arquivo ausente = on (padrao do MCP). Arquivo ilegivel = off: na duvida nao
    # se carrega modelo na GPU de quem pode estar rodando MD ou Boltz.
    if (-not (Test-Path -LiteralPath $ArqInterruptor)) {
        return [pscustomobject]@{ estado = "on"; motivo = ""; em = "" }
    }
    try {
        $sw = Get-Content -LiteralPath $ArqInterruptor -Raw -Encoding UTF8 | ConvertFrom-Json
        if (-not $sw.estado) { throw "sem campo estado" }
        return $sw
    } catch {
        return [pscustomobject]@{ estado = "off"; motivo = "arquivo do interruptor ilegivel"; em = "?" }
    }
}

function Set-Interruptor([string]$Estado, [string]$Motivo) {
    $d = [ordered]@{ estado = $Estado; motivo = $Motivo; em = (Get-Date -Format "yyyy-MM-dd HH:mm:ss") }
    New-Item -ItemType Directory -Force -Path (Split-Path $ArqInterruptor) | Out-Null
    # Sem BOM: o leitor em Python trata JSON com BOM como arquivo ausente (= on).
    [IO.File]::WriteAllText($ArqInterruptor, ($d | ConvertTo-Json), (New-Object Text.UTF8Encoding($false)))
}

function Show-Reservada($sw) {
    Write-Host "GPU reservada desde $($sw.em) ($($sw.motivo))."
    Write-Host "O LILO fica em pausa. Para devolver a GPU a ele:  .\lilo.ps1 gpu-ok"
}

# -------------------------------------------------------------------- suporte
function Test-Url([string]$Url) {
    try { $null = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3; return $true }
    catch { return $false }
}

function Wait-Ate([scriptblock]$Teste, [int]$Segundos) {
    $fim = (Get-Date).AddSeconds($Segundos)
    while ((Get-Date) -lt $fim) {
        if (& $Teste) { return $true }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Test-Docker {
    docker info --format "{{.ID}}" 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}

function Start-Motor {
    if (Test-Url "$Ollama/api/version") { return $true }
    $app = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama app.exe"
    if (-not (Test-Path $app)) { Write-Host "Ollama nao encontrado em $app"; return $false }
    Write-Host "Iniciando o Ollama..."
    Start-Process explorer.exe -ArgumentList "`"$app`""
    return (Wait-Ate { Test-Url "$Ollama/api/version" } 60)
}

function Get-Carregados {
    try { return @((Invoke-RestMethod -Uri "$Ollama/api/ps" -TimeoutSec 5).models | ForEach-Object { $_.name }) }
    catch { return @() }
}

function Get-VramLivre {
    # MiB livres na GPU; -1 se nao der para medir (ai a guarda nao barra).
    try {
        $v = (& nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits 2>$null | Select-Object -First 1)
        return [int]("$v".Trim())
    } catch { return -1 }
}

function Test-GpuDisponivel {
    # Pode carregar o modelo agora? Ja carregado conta como sim.
    if ((Get-Carregados) -contains "${Modelo}:latest") { return $true }
    $livre = Get-VramLivre
    if ($livre -ge 0 -and $livre -lt $VramMinima) {
        Write-Host "GPU ocupada por outro processo: $livre MiB de VRAM livres (o modelo precisa de $VramMinima)."
        Write-Host "Nada foi carregado. Para ver quem esta na GPU:  nvidia-smi"
        return $false
    }
    return $true
}

function Read-ParaCache([string]$Arquivo) {
    # Leitura sequencial: poe o arquivo no cache de disco do Windows. Medido em
    # 2026-10-05: com os arquivos em cache o modelo de 9 GB carrega em ~6 s; fora
    # do cache a partida leva 59-76 s.
    $fs = [IO.File]::Open($Arquivo, 'Open', 'Read', 'ReadWrite')
    try {
        $buf = New-Object byte[] (8MB)
        while ($fs.Read($buf, 0, $buf.Length) -gt 0) { }
    } finally { $fs.Close() }
}

# ------------------------------------------------------------------- comandos
function Invoke-Warm {
    $sw = Get-Interruptor
    if ($sw.estado -ne "on") { Show-Reservada $sw; return $false }
    if (-not (Start-Motor)) { Write-Host "Ollama fora do ar."; return $false }
    if (-not (Test-GpuDisponivel)) { return $false }

    $t0 = Get-Date
    $lidos = 0
    if ((Get-Carregados) -notcontains "${Modelo}:latest") {
        $arqs = @(& ollama show $Modelo --modelfile 2>$null | ForEach-Object {
                if ($_ -match '^FROM\s+(.+)$') { $Matches[1].Trim() } } |
            Where-Object { Test-Path $_ -PathType Leaf })
        $libs = Join-Path $env:LOCALAPPDATA "Programs\Ollama\lib\ollama"
        if (Test-Path $libs) {
            $arqs += @(Get-ChildItem $libs -Recurse -File -Filter *.dll |
                Where-Object { $_.DirectoryName -match 'cuda' } | ForEach-Object { $_.FullName })
        }
        Write-Host "Lendo $($arqs.Count) arquivo(s) do modelo para o cache de disco..."
        foreach ($a in $arqs) { try { Read-ParaCache $a; $lidos++ } catch { } }
    }

    # Geracao de verdade: a 1a avaliacao apos a carga tambem e lenta a frio.
    $corpo = @{ model = $Modelo; stream = $false; think = $false
        messages = @(@{ role = "user"; content = "Responda apenas: pronto" }) } | ConvertTo-Json -Depth 5
    try {
        $r = Invoke-RestMethod -Uri "$Ollama/api/chat" -Method Post -ContentType "application/json" `
            -Body ([Text.Encoding]::UTF8.GetBytes($corpo)) -TimeoutSec 300
        $seg = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
        $carga = [math]::Round($r.load_duration / 1e9, 1)
        Write-Host "Modelo '$Modelo' pronto em $seg s (carga $carga s)."
        New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
        Add-Content -Path (Join-Path $LogDir "warm.log") -Value ("{0}`t{1} s`tcarga {2} s`tpre-leitura {3} arq" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $seg, $carga, $lidos)
        return $true
    } catch {
        Write-Host "Falha ao aquecer '$Modelo': $($_.Exception.Message)"
        return $false
    }
}

function Invoke-Up {
    $sw = Get-Interruptor
    if ($sw.estado -ne "on") { Show-Reservada $sw; return $false }
    # Sem GPU para o modelo a interface nao sobe: a 1a pergunta faria o Ollama
    # carrega-lo de qualquer jeito, em cima do job que esta usando a placa.
    if ((Start-Motor) -and -not (Test-GpuDisponivel)) { return $false }
    if (-not (Test-Docker)) {
        Write-Host "Esperando o Docker Desktop..."
        if (-not (Wait-Ate { Test-Docker } 180)) { Write-Host "Docker Desktop nao respondeu."; return $false }
    }
    docker compose -f $Compose up -d
    $null = Invoke-Warm
    if (-not (Wait-Ate { Test-Url "$WebUI/health" } 120)) {
        Write-Host "A interface ainda nao respondeu em $WebUI."
        return $false
    }
    return $true
}

function Invoke-Down {
    docker compose -f $Compose stop
    foreach ($m in (Get-Carregados)) { if ($m -like "${Modelo}*") { & ollama stop $m | Out-Null } }
    Write-Host "Interface parada e modelo descarregado. O Ollama segue no ar para as outras ferramentas."
}

function Show-Status {
    $sw = Get-Interruptor
    $extra = ""
    if ($sw.em) { $extra = "  (desde $($sw.em); $($sw.motivo))" }
    Write-Host ("Interruptor de GPU: " + "$($sw.estado)".ToUpper() + $extra)
    if (Test-Url "$Ollama/api/version") { Write-Host "Ollama: no ar. Modelos carregados:"; & ollama ps }
    else { Write-Host "Ollama: FORA DO AR" }
    $g = (& nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader 2>$null)
    if ($g) { Write-Host "GPU (VRAM usada, total, uso): $g" }
    Write-Host "Interface:"
    if (Test-Docker) { docker ps -a --filter "name=lilo_openwebui" --format "  {{.Names}}  {{.Status}}" }
    else { Write-Host "  Docker Desktop fora do ar" }
    if (Test-Url "$WebUI/health") { Write-Host "  $WebUI respondendo" } else { Write-Host "  $WebUI sem resposta" }
    $b = Join-Path $LogDir "bench.jsonl"
    if (Test-Path $b) { Write-Host "Ultimo bench: $(Get-Content $b -Tail 1)" }
}

function Invoke-GpuLivre([string]$Motivo) {
    if (-not $Motivo) { $Motivo = "GPU reservada para outro job" }
    Set-Interruptor "off" $Motivo
    foreach ($m in (Get-Carregados)) { & ollama stop $m | Out-Null }
    if (Test-Docker) { docker compose -f $Compose stop | Out-Null }
    Write-Host "GPU liberada ($Motivo): interruptor OFF, modelos descarregados, interface parada."
    $g = (& nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader 2>$null)
    if ($g) { Write-Host "VRAM (usada, total): $g" }
}

function Invoke-GpuOk([string]$Opcao) {
    $sw = Get-Interruptor
    if ($sw.estado -ne "on") { Write-Host "Reserva atual: $($sw.motivo) (desde $($sw.em))." }
    $livre = Get-VramLivre
    if ($Opcao -ne "forcar" -and $livre -ge 0 -and $livre -lt $VramMinima) {
        Write-Host "A GPU ainda esta em uso: $livre MiB de VRAM livres. Interruptor mantido."
        Write-Host "Para religar mesmo assim:  .\lilo.ps1 gpu-ok forcar"
        return
    }
    Set-Interruptor "on" "liberada pelo dono (lilo.ps1 gpu-ok)"
    Write-Host "Interruptor ON."
    $null = Invoke-Up
}

switch ($Comando.ToLower()) {
    { $_ -in "abrir", "web" } {
        $ok = $true
        if (Test-Url "$WebUI/health") { $null = Invoke-Warm } else { $ok = Invoke-Up }
        if ($ok) { Start-Process $WebUI }
    }
    "up"        { $null = Invoke-Up }
    "down"      { Invoke-Down }
    "status"    { Show-Status }
    "warm"      { $null = Invoke-Warm }
    "bench"     { & $Py (Join-Path $Raiz "scripts\bench.py") @Resto; exit $LASTEXITCODE }
    "gpu-livre" { Invoke-GpuLivre ($Resto -join " ") }
    "gpu-ok"    { Invoke-GpuOk ("$($Resto | Select-Object -First 1)") }
    default {
        Write-Host "Comando desconhecido: $Comando"
        Write-Host "Use: abrir | up | down | status | warm | bench | gpu-livre [motivo] | gpu-ok [forcar]"
        exit 2
    }
}
