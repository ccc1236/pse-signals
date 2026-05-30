# PSE Signal Alert System - Docker helper
# Usage: .\pse <command> [args]
#   .\pse update          Fetch data + scan signals
#   .\pse fetch 2y        Fetch historical data
#   .\pse backtest        Run backtest
#   .\pse scan            Scan watchlist
#   .\pse dash            Start dashboard (default)
#   .\pse stop            Stop dashboard
#   .\pse logs            View dashboard logs

$cmd = $args[0]
$rest = $args[1..($args.Length)]

switch ($cmd) {
    "dash"    { docker compose up -d; Write-Host "Dashboard running at http://localhost:8050" }
    "stop"    { docker compose down }
    "logs"    { docker compose logs -f }
    "build"   { docker compose build }
    default   { docker compose exec pse-signals python main.py $cmd @rest }
}
