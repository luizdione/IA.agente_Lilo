# LILO v14 - operacao (o icone da Area de Trabalho aponta p/ ca).
#
#   .\lilo.ps1                      abre a interface (sobe o que faltar)
#   .\lilo.ps1 up                   sobe a interface e aquece o modelo
#   .\lilo.ps1 down                 para a interface e descarrega o modelo
#   .\lilo.ps1 status               interruptor, modelos na GPU, VRAM, interface
#   .\lilo.ps1 warm                 poe o modelo na GPU (leitura previa + 1 geracao)
#   .\lilo.ps1 bench [...]          mede o tempo ate o 1o token (scripts\bench.py)
#   .\lilo.ps1 convivencia [...]    portoes G1 e de recarga (scripts\convivencia.py)
#   .\lilo.ps1 presets              cria/atualiza os presets da interface (scripts\owui_presets.py)
#   .\lilo.ps1 inicio               `up` sem janela, p/ o atalho de inicializacao (log em %LOCALAPPDATA%\LILO\bench)
#   .\lilo.ps1 ponte [up|down]      ponte lilo-host (MCP HTTP em 127.0.0.1:8790): sobe, para ou mostra o estado
#   .\lilo.ps1 smoke [...]          smoke da ponte: tools por grupo e token do exec (scripts\mcp_smoke.py)
#   .\lilo.ps1 indexar [...]        indexa a biblioteca de PDFs em 2o plano (log em E:\data\lilo\biblioteca); `indexar status` mostra o progresso
#   .\lilo.ps1 gateway [up|down]    Docker MCP Gateway (paper-search, 127.0.0.1:8811) via `docker mcp gateway run`
#   .\lilo.ps1 gpu-livre [motivo]   reserva a GPU p/ MD, Boltz ou render
#   .\lilo.ps1 gpu-ok [forcar]      devolve a GPU ao LILO e aquece
#   .\lilo.ps1 code [pasta] [...]   LILO Code: OpenCode (terminal) sobre o modelo local `lilo-code` + MCP da ponte
#   .\lilo.ps1 code-run <pasta> "<tarefa>"   o mesmo sem interface (scripts\code_run.py): resumo + diff
#   .\lilo.ps1 bench agente [...]   bench AGENTICO: laco de tools de verdade (scripts\bench_agente.py)
#   .\lilo.ps1 terminal [up|down]   Open Terminal da Open WebUI no host (experimento F2b; manual)
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
$Ponte   = "http://127.0.0.1:8790"
$ArqStatusPonte = Join-Path $env:LOCALAPPDATA "LILO\host.status.json"
$Gateway = "http://127.0.0.1:8811"
$ArqPidGateway  = Join-Path $env:LOCALAPPDATA "LILO\gateway.pid"
$ArqTokenGateway = Join-Path $env:LOCALAPPDATA "LILO\gateway_token.txt"
# So buscas: o paper-search tem 57 tools, inclusive download_scihub, que fica fora.
$GatewayTools = "search_pubmed,search_europepmc,search_biorxiv,search_crossref,search_semantic"
$ArqCatalogoGateway = Join-Path $HOME ".docker\mcp\catalogs\lilo.yaml"   # scripts\gateway_catalogo.py
# Desktop Commander (o mesmo que o Claude usa nesta maquina) atras do mcpo, o proxy MCP->OpenAPI
# da propria Open WebUI: so loopback, chave = token da ponte. Guardas (comandos bloqueados,
# pastas permitidas) sao as do ~/.claude-server-commander/config.json.
$Desktop = "http://127.0.0.1:8795"
$ArqPidDesktop = Join-Path $env:LOCALAPPDATA "LILO\desktop.pid"
$DesktopCmd = @("npx", "-y", "@wonderwhy-er/desktop-commander@latest")
# Open Terminal (open-terminal, PyPI) no host: camada de acao da Open WebUI (abas de terminal, arquivos,
# diffs). Shell completo SEM deny-list: so manual (`terminal up`), nunca no `up` (decisao do autor).
$Terminal = "http://127.0.0.1:8796"
$ArqPidTerminal = Join-Path $env:LOCALAPPDATA "LILO\terminal.pid"
$ArqChaveTerminal = Join-Path $env:LOCALAPPDATA "LILO\terminal_key.txt"
# LILO Code: OpenCode (terminal) sobre o modelo local `lilo-code` (ollama\Modelfile.lilo-code).
$ModeloCode = "lilo-code"
$ConfigOpenCode = Join-Path $Raiz "opencode\opencode.json"
$RaizesCode = @("C:\GitHub", "E:\data", (Join-Path $HOME "OneDrive\Data_Science\Projetos"))

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
    Write-Host "O LILO fica em pausa (a ponte MCP do Claude segue no ar). Para devolver a GPU a ele:  .\lilo.ps1 gpu-ok"
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

# ---------------------------------------------------------------------- ponte
function Test-Ponte { return (Test-Url "$Ponte/saude") }

function Start-Ponte {
    # Servidor MCP HTTP no host (conda datascience), sem janela; log em $LogDir.
    if (Test-Ponte) { return $true }
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    $serve = Join-Path $Raiz "scripts\lilo_host_serve.py"
    Start-Process -FilePath $Py -ArgumentList "`"$serve`"" -WorkingDirectory $Raiz -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $LogDir "host.log") -RedirectStandardError (Join-Path $LogDir "host.err.log")
    if (Wait-Ate { Test-Ponte } 40) { Write-Host "Ponte lilo-host no ar em $Ponte"; return $true }
    Write-Host "A ponte nao respondeu em $Ponte (ver $LogDir\host.err.log)."
    return $false
}

function Stop-Ponte {
    if (Test-Path $ArqStatusPonte) {
        try {
            $st = Get-Content $ArqStatusPonte -Raw | ConvertFrom-Json
            Stop-Process -Id $st.pid -Force -ErrorAction SilentlyContinue
        } catch { }
        Remove-Item $ArqStatusPonte -ErrorAction SilentlyContinue
    }
    Write-Host "Ponte lilo-host parada."
}

function Get-TokenPonte {
    # Token do grupo exec, que o compose injeta em TOOL_SERVER_CONNECTIONS. Gera se faltar.
    return "$(& $Py (Join-Path $Raiz "scripts\lilo_host_serve.py") --token 2>$null | Select-Object -Last 1)".Trim()
}

function Invoke-Indexar([string[]]$Args) {
    # Biblioteca de PDFs (F3): incremental e sob demanda (D-0016). `status`/`falhas` respondem na hora;
    # o resto vai para segundo plano com log, porque indexar 1.100 PDFs leva dezenas de minutos.
    $script = Join-Path $Raiz "scripts\indexar_biblioteca.py"
    $o = "$($Args | Select-Object -First 1)".ToLower()
    if ($o -eq "status" -or $o -eq "falhas") { & $Py $script "--$o"; return }
    $indice = if ($env:LILO_BIBLIOTECA) { $env:LILO_BIBLIOTECA } else { "E:\data\lilo\biblioteca" }
    New-Item -ItemType Directory -Force -Path $indice | Out-Null
    $log = Join-Path $indice "indexar.log"
    $lista = @("-u", "`"$script`"") + $Args   # -u: log sem buffer (stdout redirecionado)
    Start-Process -FilePath $Py -ArgumentList $lista -WorkingDirectory $Raiz -WindowStyle Hidden `
        -RedirectStandardOutput $log -RedirectStandardError (Join-Path $indice "indexar.err.log")
    Write-Host "Indexacao iniciada em segundo plano. Acompanhe:  .\lilo.ps1 indexar status   (log: $log)"
}

function Test-Gateway {
    try { $r = Invoke-WebRequest -Uri "$Gateway/mcp" -UseBasicParsing -TimeoutSec 3; return $true }
    catch { return ($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -in 400, 401, 405, 406) }
}

function Get-TokenGateway {
    if (-not (Test-Path $ArqTokenGateway)) {
        New-Item -ItemType Directory -Force -Path (Split-Path $ArqTokenGateway) | Out-Null
        $bytes = New-Object byte[] 32; (New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($bytes)
        [IO.File]::WriteAllText($ArqTokenGateway, ([Convert]::ToBase64String($bytes) -replace "[/+=]", "x"), (New-Object Text.UTF8Encoding($false)))
    }
    return (Get-Content $ArqTokenGateway -Raw).Trim()
}

function Start-Gateway {
    # Literatura (F4): o gateway da Docker roda no host, preso ao loopback, com token; a ponte
    # lilo-host o encaminha em /literatura/mcp (o gateway so aceita Host localhost).
    if (Test-Gateway) { return $true }
    if (-not (Test-Docker)) { Write-Host "Docker Desktop fora do ar: gateway de literatura nao sobe."; return $false }
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    # O gateway 0.43 le o catalogo de ARQUIVO (~/.docker/mcp/catalogs/); sem ele sobe com 0 tools.
    if (-not (Test-Path $ArqCatalogoGateway)) {
        & $Py (Join-Path $Raiz "scripts\gateway_catalogo.py") 2>&1 | Select-Object -Last 2 | Out-Host
        if (-not (Test-Path $ArqCatalogoGateway)) { Write-Host "Sem catalogo do gateway: literatura nao sobe."; return $false }
    }
    $env:MCP_GATEWAY_AUTH_TOKEN = Get-TokenGateway
    $args = @("mcp", "gateway", "run", "--transport", "streaming", "--host", "127.0.0.1", "--port", "8811",
              "--catalog", (Split-Path $ArqCatalogoGateway -Leaf),
              "--servers", "paper-search", "--tools", $GatewayTools, "--long-lived")
    $p = Start-Process -FilePath "docker" -ArgumentList $args -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $LogDir "gateway.log") -RedirectStandardError (Join-Path $LogDir "gateway.err.log")
    Set-Content -Path $ArqPidGateway -Value $p.Id
    if (Wait-Ate { Test-Gateway } 90) { Write-Host "Gateway de literatura no ar em $Gateway"; return $true }
    Write-Host "O gateway nao respondeu em $Gateway (ver $LogDir\gateway.err.log)."
    return $false
}

function Stop-Gateway {
    if (Test-Path $ArqPidGateway) {
        # `docker mcp` e um plugin da CLI: o gateway de verdade e um FILHO (docker-mcp.exe); matar so
        # o pai deixa a porta 8811 ocupada por um orfao sem catalogo -> taskkill com a arvore inteira.
        try { & taskkill /PID ([int](Get-Content $ArqPidGateway -Raw).Trim()) /T /F 2>$null | Out-Null } catch { }
        Remove-Item $ArqPidGateway -ErrorAction SilentlyContinue
    }
    Write-Host "Gateway de literatura parado."
}

function Show-Gateway {
    if (Test-Gateway) { Write-Host "Gateway de literatura: $Gateway respondendo" } else { Write-Host "Gateway de literatura: parado" }
}

function Update-CaBundle {
    # O Kaspersky inspeciona HTTPS com raiz propria (confiada so pelo Windows); o Linux do container
    # a recusa e a Claude falha com CERTIFICATE_VERIFY_FAILED. Bundle montado no compose
    # (SSL_CERT_FILE) = certifi do container + raizes do Kaspersky. Idempotente.
    $dir = Join-Path $env:LOCALAPPDATA "LILO"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $certifi = Join-Path $dir "certifi.pem"
    $bundle = Join-Path $dir "ca-bundle.pem"
    if (-not (Test-Path $certifi)) {
        docker cp lilo_openwebui:/usr/local/lib/python3.11/site-packages/certifi/cacert.pem $certifi 2>$null | Out-Null
        if (-not (Test-Path $certifi)) {
            docker run --rm --entrypoint cat ghcr.io/open-webui/open-webui:v0.11.4 /usr/local/lib/python3.11/site-packages/certifi/cacert.pem | Out-File -Encoding ascii $certifi
        }
    }
    if (-not (Test-Path $certifi)) { Write-Host "Sem certifi.pem: bundle de CAs nao gerado."; return }
    $extras = @(Get-ChildItem Cert:\CurrentUser\Root, Cert:\LocalMachine\Root -ErrorAction SilentlyContinue |
                Where-Object { $_.Subject -match "Kaspersky" } | Sort-Object Thumbprint -Unique)
    $pem = @(Get-Content $certifi)
    foreach ($c in $extras) {
        $pem += "# " + $c.Subject
        $pem += "-----BEGIN CERTIFICATE-----"
        $pem += ([Convert]::ToBase64String($c.RawData, "InsertLineBreaks") -split "`r?`n")
        $pem += "-----END CERTIFICATE-----"
    }
    $novo = ($pem -join "`n") + "`n"
    if (-not (Test-Path $bundle) -or ((Get-Content $bundle -Raw) -ne $novo)) {
        [IO.File]::WriteAllText($bundle, $novo, (New-Object Text.UTF8Encoding($false)))
    }
    Write-Host "Bundle de CAs do container: $($extras.Count) raiz(es) extra(s) ($bundle)"
}

function Get-EnvArquivo([string]$Chave) {
    # Le UMA chave do .env do repo (nunca o imprime nem o move).
    $arq = Join-Path $Raiz ".env"
    if (-not (Test-Path $arq)) { return "" }
    foreach ($l in Get-Content $arq) {
        if ($l -match "^\s*$Chave\s*=\s*(.*)$") { return $Matches[1].Trim().Trim('"').Trim("'") }
    }
    return ""
}

function Test-Desktop([string]$Tok) {
    try {
        $r = Invoke-WebRequest -Uri "$Desktop/openapi.json" -Headers @{ Authorization = "Bearer $Tok" } -UseBasicParsing -TimeoutSec 3
        return ($r.StatusCode -eq 200)
    } catch { return $false }
}

function Start-Desktop {
    # Desktop Commander no host, atras do mcpo (MCP stdio -> OpenAPI), so loopback, chave = token
    # da ponte (a interface entra com o mesmo Bearer do grupo exec). O npx resolve e cacheia o pacote.
    $tok = Get-TokenPonte
    if (Test-Desktop $tok) { return $true }
    $mcpo = Join-Path (Split-Path $Py) "mcpo.exe"
    if (-not (Test-Path $mcpo)) { Write-Host "mcpo nao esta no env do projeto ($mcpo): pip install mcpo"; return $false }
    if (-not (Get-Command npx -ErrorAction SilentlyContinue)) { Write-Host "npx (Node.js) nao encontrado: Desktop Commander nao sobe."; return $false }
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    $args = @("--host", "127.0.0.1", "--port", "8795", "--api-key", $tok, "--") + $DesktopCmd
    $p = Start-Process -FilePath $mcpo -ArgumentList $args -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $LogDir "desktop.log") -RedirectStandardError (Join-Path $LogDir "desktop.err.log")
    Set-Content -Path $ArqPidDesktop -Value $p.Id
    if (Wait-Ate { Test-Desktop $tok } 120) { Write-Host "Desktop Commander no ar em $Desktop (mcpo)"; return $true }
    Write-Host "O Desktop Commander nao respondeu em $Desktop (ver $LogDir\desktop.err.log)."
    return $false
}

function Stop-Desktop {
    if (Test-Path $ArqPidDesktop) {
        # mcpo -> npx -> node: matar a arvore, senao o Desktop Commander fica orfao na porta.
        try { & taskkill /PID ([int](Get-Content $ArqPidDesktop -Raw).Trim()) /T /F 2>$null | Out-Null } catch { }
        Remove-Item $ArqPidDesktop -ErrorAction SilentlyContinue
    }
    Write-Host "Desktop Commander parado."
}

function Show-Desktop {
    if (Test-Desktop (Get-TokenPonte)) { Write-Host "Desktop Commander: $Desktop respondendo (mcpo)" } else { Write-Host "Desktop Commander: parado" }
}

function Show-Ponte {
    if (Test-Ponte) { Write-Host "Ponte lilo-host: $Ponte respondendo" } else { Write-Host "Ponte lilo-host: parada" }
}

# ------------------------------------------------------ Open Terminal (F2b, manual)
function Get-ChaveTerminal {
    if (Test-Path $ArqChaveTerminal) { $k = (Get-Content $ArqChaveTerminal -Raw).Trim(); if ($k) { return $k } }
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $k = ([Convert]::ToBase64String($bytes)).Replace("+", "-").Replace("/", "_").TrimEnd("=")
    New-Item -ItemType Directory -Force -Path (Split-Path $ArqChaveTerminal) | Out-Null
    Set-Content -Path $ArqChaveTerminal -Value $k -NoNewline
    return $k
}

function Test-Terminal {
    try {
        $r = Invoke-WebRequest -Uri "$Terminal/health" -UseBasicParsing -TimeoutSec 3
        return ($r.StatusCode -eq 200)
    } catch { return $false }
}

function Start-Terminal {
    if (Test-Terminal) { return $true }
    $exe = Get-Command open-terminal -ErrorAction SilentlyContinue
    if (-not $exe) { Write-Host "open-terminal nao encontrado. Instale (uma vez):  uv tool install open-terminal==0.14.6"; return $false }
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    $null = Get-ChaveTerminal
    # PS 5.1 nao tem Start-Process -Environment: o filho herda o ambiente do processo.
    $antes = @{}
    $novo = @{ OPEN_TERMINAL_API_KEY_FILE = $ArqChaveTerminal; PYTHONUTF8 = "1";
               OPEN_TERMINAL_EXECUTE_TIMEOUT = "30"; OPEN_TERMINAL_CORS_ALLOWED_ORIGINS = "http://127.0.0.1:3000";
               OPEN_TERMINAL_SYSTEM_PROMPT = "Terminal do host Windows do dono. O shell e o cmd.exe: para PowerShell use `powershell -NoProfile -Command ...`. Python e o do conda datascience (no PATH), R e Rscript, WSL e wsl. Saidas longas: use tail. Responda em portugues." }
    foreach ($k in $novo.Keys) { $antes[$k] = [Environment]::GetEnvironmentVariable($k); [Environment]::SetEnvironmentVariable($k, $novo[$k]) }
    try {
        $p = Start-Process -FilePath $exe.Source -ArgumentList @("run", "--host", "127.0.0.1", "--port", "8796", "--cwd", "C:\GitHub") `
            -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $LogDir "terminal.log") -RedirectStandardError (Join-Path $LogDir "terminal.err.log")
        Set-Content -Path $ArqPidTerminal -Value $p.Id
    } finally {
        foreach ($k in $novo.Keys) { [Environment]::SetEnvironmentVariable($k, $antes[$k]) }
    }
    if (Wait-Ate { Test-Terminal } 60) { Write-Host "Open Terminal no ar em $Terminal (chave em $ArqChaveTerminal)"; return $true }
    Write-Host "O Open Terminal nao respondeu em $Terminal (ver $LogDir\terminal.err.log)."
    return $false
}

function Stop-Terminal {
    if (Test-Path $ArqPidTerminal) {
        try { & taskkill /PID ([int](Get-Content $ArqPidTerminal -Raw).Trim()) /T /F 2>$null | Out-Null } catch { }
        Remove-Item $ArqPidTerminal -ErrorAction SilentlyContinue
    }
    Write-Host "Open Terminal parado."
}

function Show-Terminal {
    if (Test-Terminal) { Write-Host "Open Terminal: $Terminal respondendo" } else { Write-Host "Open Terminal: parado (experimento; lilo.ps1 terminal up)" }
}

# ------------------------------------------------------------- LILO Code
function Invoke-Code([string[]]$ArgsOC) {
    # OpenCode sobre o modelo local: falha fechada no interruptor, ponte + token, troca o modelo da
    # GPU (lilo -> lilo-code) e devolve o lilo ao sair.
    $sw = Get-Interruptor
    if ($sw.estado -ne "on") { Show-Reservada $sw; exit 3 }
    if (-not (Start-Motor)) { Write-Host "Ollama nao subiu."; exit 2 }
    $oc = Get-Command opencode -ErrorAction SilentlyContinue
    if (-not $oc) { Write-Host "OpenCode nao encontrado. Instale (uma vez):  npm install -g opencode-ai@1.19.5"; exit 2 }
    $pasta = (Get-Location).Path
    $resto = @()
    if ($ArgsOC -and $ArgsOC.Count -gt 0) {
        if ($ArgsOC[0] -and -not $ArgsOC[0].StartsWith("-")) { $pasta = $ArgsOC[0]; if ($ArgsOC.Count -gt 1) { $resto = $ArgsOC[1..($ArgsOC.Count - 1)] } }
        else { $resto = $ArgsOC }
    }
    try { $pasta = (Resolve-Path $pasta -ErrorAction Stop).Path } catch { Write-Host "pasta nao existe: $pasta"; exit 2 }
    $dentro = $false
    foreach ($r in $RaizesCode) { if ($pasta.ToLower().StartsWith($r.ToLower())) { $dentro = $true } }
    if (-not $dentro) { Write-Host "Pasta fora de $($RaizesCode -join ', '): $pasta"; exit 2 }
    $tem = (& ollama show $ModeloCode 2>$null)
    if (-not $tem) {
        Write-Host "Criando o modelo $ModeloCode (ollama\Modelfile.lilo-code)..."
        & ollama create $ModeloCode -f (Join-Path $Raiz "ollama\Modelfile.lilo-code") | Out-Host
    }
    $null = Start-Ponte
    $env:LILO_HOST_TOKEN = Get-TokenPonte
    foreach ($m in (Get-Carregados)) { if ($m -like "${Modelo}:*" -or $m -eq $Modelo) { & ollama stop $m | Out-Null } }
    Write-Host "Aquecendo $ModeloCode..."
    try {
        $null = Invoke-RestMethod -Method Post -Uri "$Ollama/api/chat" -ContentType "application/json" -TimeoutSec 300 `
            -Body (@{ model = $ModeloCode; stream = $false; messages = @(@{ role = "user"; content = "Responda apenas: pronto" }) } | ConvertTo-Json -Depth 5)
        $ps = Invoke-RestMethod -Uri "$Ollama/api/ps" -TimeoutSec 10
        foreach ($m in $ps.models) { if ("$($m.name)".StartsWith($ModeloCode)) { Write-Host ("  contexto {0} | VRAM {1:N1} de {2:N1} GB" -f $m.context_length, ($m.size_vram / 1GB), ($m.size / 1GB)) } }
    } catch { Write-Host "Aquecimento falhou: $_" }
    $env:OPENCODE_CONFIG = $ConfigOpenCode
    $env:OPENCODE_DISABLE_AUTOUPDATE = "1"
    $env:OPENCODE_DISABLE_CLAUDE_CODE_PROMPT = "1"      # senao importa ~/.claude/CLAUDE.md (13 KB) no prompt
    $env:OPENCODE_DISABLE_CLAUDE_CODE_SKILLS = "1"
    $env:PYTHONUTF8 = "1"
    $env:PATH = (Split-Path $Py) + ";" + (Join-Path (Split-Path $Py) "Scripts") + ";" + $env:PATH
    Push-Location $pasta
    try { & $oc.Source @resto }
    finally {
        Pop-Location
        Remove-Item Env:\LILO_HOST_TOKEN -ErrorAction SilentlyContinue
        & ollama stop $ModeloCode 2>$null | Out-Null
        $null = Invoke-Warm      # devolve o `lilo` a GPU
    }
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
    # A ponte nao usa a GPU (le o interruptor antes de chamar o Ollama) e o Claude Code depende dela
    # (MCP lilo-conhecimento e lilo-analise): sobe mesmo com a GPU reservada. Em 14/10 ela ficou fora
    # porque o `up`/`inicio` paravam no interruptor OFF antes de chega-la.
    $null = Start-Ponte
    $sw = Get-Interruptor
    if ($sw.estado -ne "on") { Show-Reservada $sw; return $false }
    # Sem GPU para o modelo a interface nao sobe: a 1a pergunta faria o Ollama
    # carrega-lo de qualquer jeito, em cima do job que esta usando a placa.
    if ((Start-Motor) -and -not (Test-GpuDisponivel)) { return $false }
    if (-not (Test-Docker)) {
        Write-Host "Esperando o Docker Desktop..."
        if (-not (Wait-Ate { Test-Docker } 180)) { Write-Host "Docker Desktop nao respondeu."; return $false }
    }
    # A ponte sobe antes da interface e o token do exec entra no compose pelo ambiente.
    $null = Start-Ponte
    $null = Start-Gateway
    # Desktop Commander (mcpo, so loopback, token da ponte) sobe junto: decisao do autor em 13/10
    # (antes era so `lilo.ps1 desktop up`, manual; I-0018).
    $null = Start-Desktop
    $env:LILO_HOST_TOKEN = Get-TokenPonte
    # Claude na interface (OPENAI_API_KEYS do compose): a chave sai do .env do repo, sem passar
    # por arquivo versionado nem pela tela.
    $env:ANTHROPIC_API_KEY = Get-EnvArquivo "ANTHROPIC_API_KEY"
    Update-CaBundle
    docker compose -f $Compose up -d
    $null = Invoke-Warm
    if (-not (Wait-Ate { Test-Url "$WebUI/health" } 120)) {
        Write-Host "A interface ainda nao respondeu em $WebUI."
        return $false
    }
    # Presets (LILO, Pesquisa, Analise) sao registros no volume da interface:
    # idempotente, ~1 s, e deixa um volume novo pronto sem clicar em nada.
    & $Py (Join-Path $Raiz "scripts\owui_presets.py") 2>&1 | Select-Object -First 3 | Out-Host
    # Filtros da interface (botoes da caixa de mensagem e valves do painel direito).
    & $Py (Join-Path $Raiz "scripts\owui_funcoes.py") 2>&1 | Select-Object -First 5 | Out-Host
    return $true
}

function Invoke-Inicio {
    # Atalho de inicializacao do Windows (sem janela): tudo vai para o log.
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    Start-Transcript -Path (Join-Path $LogDir "inicio.log") -Append | Out-Null
    try {
        Write-Host "--- $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') lilo.ps1 inicio"
        $ok = Invoke-Up
        if ($ok) { Write-Host "Resultado: LILO no ar." } else { Write-Host "Resultado: nao subiu (ver acima)." }
    } finally { Stop-Transcript | Out-Null }
}

function Invoke-Down {
    docker compose -f $Compose stop
    foreach ($m in (Get-Carregados)) { if ($m -like "${Modelo}*") { & ollama stop $m | Out-Null } }
    Stop-Ponte
    Stop-Gateway
    Stop-Desktop
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
    Show-Ponte
    Show-Gateway
    Show-Desktop
    Show-Terminal
    $b = Join-Path $LogDir "bench.jsonl"
    if (Test-Path $b) { Write-Host "Ultimo bench: $(Get-Content $b -Tail 1)" }
    $ag = Join-Path $LogDir "agente.jsonl"
    if (Test-Path $ag) { Write-Host "Ultimo bench agente: $(Get-Content $ag -Tail 1)" }
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
    "bench"     {
        $o = "$($Resto | Select-Object -First 1)".ToLower()
        if ($o -eq "agente") {
            $r2 = @(); if ($Resto.Count -gt 1) { $r2 = $Resto[1..($Resto.Count - 1)] }
            & $Py (Join-Path $Raiz "scripts\bench_agente.py") @r2; exit $LASTEXITCODE
        }
        & $Py (Join-Path $Raiz "scripts\bench.py") @Resto; exit $LASTEXITCODE
    }
    "code"      { Invoke-Code $Resto }
    "code-run"  { & $Py (Join-Path $Raiz "scripts\code_run.py") @Resto; exit $LASTEXITCODE }
    "terminal"  {
        $o = "$($Resto | Select-Object -First 1)".ToLower()
        if ($o -eq "up") { $null = Start-Terminal } elseif ($o -eq "down") { Stop-Terminal } else { Show-Terminal }
    }
    "convivencia" { & $Py (Join-Path $Raiz "scripts\convivencia.py") @Resto; exit $LASTEXITCODE }
    "presets"   {
        & $Py (Join-Path $Raiz "scripts\owui_presets.py") @Resto
        & $Py (Join-Path $Raiz "scripts\owui_funcoes.py") @Resto
        exit $LASTEXITCODE
    }
    "inicio"    { Invoke-Inicio }
    "ponte"     {
        $o = "$($Resto | Select-Object -First 1)".ToLower()
        if ($o -eq "up") { $null = Start-Ponte } elseif ($o -eq "down") { Stop-Ponte } else { Show-Ponte }
    }
    "smoke"     { & $Py (Join-Path $Raiz "scripts\mcp_smoke.py") @Resto; exit $LASTEXITCODE }
    "gateway"   {
        $o = "$($Resto | Select-Object -First 1)".ToLower()
        if ($o -eq "up") { $null = Start-Gateway } elseif ($o -eq "down") { Stop-Gateway } else { Show-Gateway }
    }
    "desktop"   {
        $o = "$($Resto | Select-Object -First 1)".ToLower()
        if ($o -eq "up") { $null = Start-Desktop } elseif ($o -eq "down") { Stop-Desktop } else { Show-Desktop }
    }
    "indexar"   { Invoke-Indexar $Resto }
    "gpu-livre" { Invoke-GpuLivre ($Resto -join " ") }
    "gpu-ok"    { Invoke-GpuOk ("$($Resto | Select-Object -First 1)") }
    default {
        Write-Host "Comando desconhecido: $Comando"
        Write-Host "Use: abrir | up | down | status | warm | bench [agente] | convivencia | presets | inicio | ponte [up|down] | gateway [up|down] | desktop [up|down] | terminal [up|down] | smoke | indexar [status|falhas|...] | gpu-livre [motivo] | gpu-ok [forcar] | code [pasta] | code-run <pasta> <tarefa>"
        exit 2
    }
}
