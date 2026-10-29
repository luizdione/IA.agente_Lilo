# f1_bakeoff.ps1 - bake-off da F1 do plano "LILO age" (28/10) num comando so, para rodar no dia do gpu-ok.
#
#   .\scripts\f1_bakeoff.ps1                 # cria as 3 candidatas e roda tudo (1-2 h com a GPU quieta)
#   .\scripts\f1_bakeoff.ps1 -Modelos cand-coder,cand-2507 -Repeticoes 2
#
# Passos: (1) interruptor tem de estar ON (falha fechada); (2) ponte no ar; (3) `ollama create` das
# candidatas a partir de ollama\Modelfile.cand-*; (4) por candidata: bench agente (4 tarefas x N),
# bench de chat (ollama, --sem-portao) e bakeoff_tools (8 pedidos); (5) imprime onde ficaram os
# resultados. NAO roda nada em paralelo com o lumen (/api/embed) nem com outro job na GPU: o
# bench_agente.py checa isso e sai com 3. Compativel com Windows PowerShell 5.1 (so ASCII).
param(
    [string[]]$Modelos = @("cand-coder", "cand-2507", "cand-oss"),
    [int]$Repeticoes = 3,
    [switch]$SemCriar
)
$ErrorActionPreference = "Continue"
$Raiz = Split-Path $PSScriptRoot
$Lilo = Join-Path $Raiz "lilo.ps1"
$Py = if ($env:LILO_PY) { $env:LILO_PY } else { Join-Path $env:USERPROFILE "miniforge3\envs\datascience\python.exe" }
$Sw = Join-Path $env:USERPROFILE ".ollama_delegate\switch.json"
$Log = Join-Path $env:LOCALAPPDATA "LILO\bench"

$estado = "off"
try { if (Test-Path $Sw) { $estado = "$((Get-Content $Sw -Raw | ConvertFrom-Json).estado)".ToLower() } else { $estado = "on" } } catch { $estado = "off" }
if ($estado -ne "on") { Write-Host "Interruptor de GPU OFF (ou ilegivel): rode .\lilo.ps1 gpu-ok primeiro. Nada foi carregado."; exit 3 }

& powershell -NoProfile -ExecutionPolicy Bypass -File $Lilo ponte up | Out-Host
if (-not $SemCriar) {
    foreach ($m in $Modelos) {
        $mf = Join-Path $Raiz ("ollama\Modelfile." + $m)
        if (-not (Test-Path $mf)) { Write-Host "sem Modelfile para $m ($mf)"; continue }
        Write-Host "== ollama create $m"
        & ollama create $m -f $mf | Out-Host
    }
}
$inicio = Get-Date
Write-Host "== bench agente ($($Modelos -join ',') x $Repeticoes repeticoes)"
& $Py (Join-Path $Raiz "scripts\bench_agente.py") --modelos ($Modelos -join ",") --repeticoes $Repeticoes --salvar-transcricao --sem-portao | Out-Host
$rcAgente = $LASTEXITCODE
foreach ($m in $Modelos) {
    Write-Host "== bench de chat: $m"
    & $Py (Join-Path $Raiz "scripts\bench.py") --alvo ollama --modelo $m --sem-portao | Out-Host
    & ollama stop $m 2>$null | Out-Null
}
Write-Host "== bakeoff_tools (8 pedidos, caminho ollama)"
& $Py (Join-Path $Raiz "scripts\bakeoff_tools.py") --modelos ($Modelos -join ",") --caminho ollama | Out-Host
foreach ($m in $Modelos) { & ollama stop $m 2>$null | Out-Null }
$dur = [math]::Round(((Get-Date) - $inicio).TotalMinutes)
Write-Host ""
Write-Host "F1 terminou em $dur min (bench agente saiu com $rcAgente)."
Write-Host "Resultados: $Log\agente.jsonl (linhas tipo=resumo), $Log\bench.jsonl, transcricoes em $Log\agente\"
Write-Host "Proximo: decidir a base (regra em PROJECT_STATE: passa G-B e G-A -> Modelfile.lilo e lilo-code)."
& powershell -NoProfile -ExecutionPolicy Bypass -File $Lilo warm | Out-Host
