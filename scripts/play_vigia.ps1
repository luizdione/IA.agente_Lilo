# play_vigia.ps1 - "play" no Docker Desktop = lilo.ps1 gpu-ok   (pedido do autor, 2026-10-13)
#
# Um container nao consegue rodar nada no host. Este script fica escutando os eventos do Docker e,
# quando o container da interface (lilo_openwebui) e INICIADO com o interruptor da GPU em OFF,
# entende que o dono deu play querendo o LILO e roda `lilo.ps1 gpu-ok` (interruptor ON, ponte,
# gateway, Desktop Commander, aquecimento, presets). Com o interruptor ON o evento e o `up` normal
# e nada acontece. Se a GPU ainda estiver ocupada (uso >= 50%, ou VRAM cheia - o gpu-ok recusa),
# a interface e parada de novo: sem GPU ela nao pode ficar no ar (a 1a pergunta carregaria o
# modelo em cima do job).
#
# Como usar, com janela:
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\GitHub\LILO\scripts\play_vigia.ps1
# Sem janela e em todo logon: atalho na pasta Inicializacao (Win+R -> shell:startup) com o alvo
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\GitHub\LILO\scripts\play_vigia.ps1"
# Log: %LOCALAPPDATA%\LILO\bench\play-vigia.log. Compativel com Windows PowerShell 5.1: so ASCII.
param([int]$UsoMaximo = 50)

$Raiz = Split-Path $PSScriptRoot
$Lilo = Join-Path $Raiz "lilo.ps1"
$Compose = Join-Path $Raiz "compose.yaml"
$ArqInterruptor = Join-Path $env:USERPROFILE ".ollama_delegate\switch.json"
$LogDir = Join-Path $env:LOCALAPPDATA "LILO\bench"

function Get-Estado {
    # Mesma regra do lilo.ps1: arquivo ausente = on (padrao do MCP); ilegivel = off (falha fechada).
    if (-not (Test-Path -LiteralPath $ArqInterruptor)) { return "on" }
    try { return "$((Get-Content -LiteralPath $ArqInterruptor -Raw -Encoding UTF8 | ConvertFrom-Json).estado)".ToLower() }
    catch { return "off" }
}
function Get-GpuUso {
    # Utilizacao da GPU em % (-1 se o nvidia-smi nao responder). O gpu-ok so olha a VRAM; aqui
    # olha-se tambem o uso, porque uma MD ocupa 2 GB de VRAM e 90% de computo.
    $u = (& nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>$null)
    if ($u -and "$u".Trim() -match '^\d+$') { return [int]"$u".Trim() }
    return -1
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Start-Transcript -Path (Join-Path $LogDir "play-vigia.log") -Append | Out-Null
try {
    Write-Host "--- $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') vigia do play no ar (pid $PID): escutando lilo_openwebui"
    while ($true) {
        $null = (& docker info 2>$null)
        if ($LASTEXITCODE -ne 0) { Start-Sleep -Seconds 30; continue }
        & docker events --filter "container=lilo_openwebui" --filter "event=start" --format "{{.Time}}" 2>$null | ForEach-Object {
            if ((Get-Estado) -eq "on") { return }   # `lilo.ps1 up` normal: nada a fazer
            $uso = Get-GpuUso
            Write-Host "--- $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') play no container com o interruptor OFF; GPU em uso: $uso%"
            if ($uso -ge $UsoMaximo) { Write-Host "GPU ocupada por outro job ($uso%): interruptor mantido." }
            else { & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Lilo gpu-ok }
            if ((Get-Estado) -ne "on") {
                & docker compose -f $Compose stop 2>$null | Out-Null
                Write-Host "Interface parada de novo. Quando o job acabar, de play outra vez (ou lilo.ps1 gpu-ok forcar)."
            }
        }
        Start-Sleep -Seconds 5   # o docker events caiu (Docker reiniciou?): volta a escutar
    }
} finally { Stop-Transcript | Out-Null }
