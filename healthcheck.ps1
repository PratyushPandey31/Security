Start-Sleep 8
Write-Host "--- Service Health Check ---"

$urls = @{
    "Backend API" = "http://localhost:5000/api/stats"
    "Dashboard"   = "http://localhost:8081"
    "Web App"     = "http://localhost:8000"
    "WAF Proxy"   = "http://localhost:8080"
}

foreach ($svc in $urls.GetEnumerator()) {
    try {
        $r = Invoke-WebRequest -Uri $svc.Value -UseBasicParsing -TimeoutSec 5
        Write-Host "$($svc.Key): OK ($($r.StatusCode))"
    } catch {
        Write-Host "$($svc.Key): FAIL - $($_.Exception.Message)"
    }
}
