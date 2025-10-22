 # bootstrap/bootstrap-install.ps1                                                                                 
  param(                                                                                                            
      [switch]$Elevated                                                                                             
  )                                                                                                                 
                                                                                                                    
  $ErrorActionPreference = "Stop"                                                                                   
                                                                                                                    
  function Write-Status {                                                                                           
      param(                                                                                                        
          [string]$Message,                                                                                         
          [ConsoleColor]$Color = [ConsoleColor]::Gray                                                               
      )                                                                                                             
      Write-Host $Message -ForegroundColor $Color                                                                   
  }
                                                                                                                    
  function Test-IsAdmin {                                                                                           
      $identity = [Security.Principal.WindowsIdentity]::GetCurrent()                                                
      $principal = New-Object Security.Principal.WindowsPrincipal($identity)                                        
      return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)                            
  }                                                                                                                 
                                                                                                                    
  function Get-PythonCandidates {                                                                                   
      param([string]$RepoRoot)                                                                                       
                                                                                                                     
      $candidates = @()                                                                                              
      $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"                                                   
      if (Test-Path $venvPython) {                                                                                   
          $candidates += [PSCustomObject]@{ Path = $venvPython; Args = @() }                                          
      }                                                                                                              
                                                                                                                     
      foreach ($name in @("python.exe", "python3.exe", "python3", "python")) {                                       
          try {                                                                                                      
              $command = Get-Command $name -ErrorAction Stop                                                         
              if ($command -and $command.Path) {                                                                     
                  $candidates += [PSCustomObject]@{ Path = $command.Path; Args = @() }                                
              }                                                                                                      
          } catch {}                                                                                                 
      }                                                                                                              
                                                                                                                     
      $localPythonRoot = Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "Programs\Python"          
      if (Test-Path $localPythonRoot) {                                                                              
          try {                                                                                                      
              $installations = Get-ChildItem -Path $localPythonRoot -Directory -ErrorAction Stop | Sort-Object Name -Descending
              foreach ($installation in $installations) {                                                            
                  $exe = Join-Path $installation.FullName "python.exe"                                               
                  if (Test-Path $exe) {                                                                              
                      $candidates += [PSCustomObject]@{ Path = $exe; Args = @() }                                     
                  }                                                                                                  
              }                                                                                                      
          } catch {}                                                                                                 
      }                                                                                                              
                                                                                                                     
      try {                                                                                                          
          $pyLauncher = Get-Command "py" -ErrorAction Stop                                                           
          if ($pyLauncher -and $pyLauncher.Path) {                                                                   
              $candidates += [PSCustomObject]@{ Path = $pyLauncher.Path; Args = @("-3") }                             
          }                                                                                                          
      } catch {}                                                                                                     
                                                                                                                     
      return $candidates                                                                                             
  }                                                                                                                  
                                                                                                                    
  function Test-PythonCandidate {                                                                                   
      param([string]$Path, [string[]]$Args)                                                                         
                                                                                                                    
      $commandArgs = @()                                                                                            
      if ($Args) { $commandArgs += $Args }                                                                          
      $commandArgs += "-c"                                                                                          
      $commandArgs += "import sys; sys.exit(0 if sys.version_info[:2] >= (3, 11) else 1)"                           
                                                                                                                    
      try {                                                                                                         
          & $Path @commandArgs *> $null                                                                             
          return $LASTEXITCODE -eq 0                                                                                
      } catch {                                                                                                     
          return $false                                                                                             
      }                                                                                                             
  }                                                                                                                 
                                                                                                                    
  function Install-PythonRuntime {                                                                                   
      param([string]$DownloadUrl)                                                                                    
                                                                                                                     
      Write-Status "Downloading Python runtime from $DownloadUrl ..." Cyan                                           
      $tempDir = [IO.Path]::GetTempPath()                                                                           
      $installerPath = Join-Path $tempDir ("fcc-python-" + [IO.Path]::GetRandomFileName() + ".exe")                 
                                                                                                                     
      try {                                                                                                         
          try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}          
          Invoke-WebRequest -Uri $DownloadUrl -OutFile $installerPath -UseBasicParsing                              
      } catch {                                                                                                     
          throw "Failed to download Python installer: $($_.Exception.Message)"                                     
      }                                                                                                             
                                                                                                                     
      Write-Status "Running Python installer (silent)..." Cyan                                                      
      $arguments = @(                                                                                               
          "/quiet","InstallAllUsers=0","Include_test=0",                                                            
          "Include_launcher=1","Include_pip=1","PrependPath=1"                                                      
      )                                                                                                            
      $process = Start-Process -FilePath $installerPath -ArgumentList $arguments -Wait -PassThru                    
      if ($process.ExitCode -ne 0) {                                                                               
          throw "Python installer exited with code $($process.ExitCode)"                                           
      }                                                                                                            
                                                                                                                     
      Remove-Item $installerPath -Force -ErrorAction SilentlyContinue                                               
                                                                                                                     
      $localPythonRoot = Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "Programs\Python"          
      if (Test-Path $localPythonRoot) {                                                                              
          try {                                                                                                      
              $pythonExe = Get-ChildItem -Path $localPythonRoot -Filter "python.exe" -Recurse -ErrorAction Stop |   
                  Sort-Object FullName -Descending |                                                                 
                  Select-Object -First 1                                                                             
              if ($pythonExe) {                                                                                      
                  return [PSCustomObject]@{ Path = $pythonExe.FullName; Args = @() }                                 
              }                                                                                                      
          } catch {}                                                                                                 
      }                                                                                                              
                                                                                                                     
      return $null                                                                                                   
  }                                                                                                                 
                                                                                                                    
  function Ensure-Python {                                                                                           
      param([string]$RepoRoot)                                                                                       
                                                                                                                     
      $downloadUrl = $env:FCC_PYTHON_INSTALLER_URL                                                                   
      if (-not $downloadUrl) {                                                                                       
          $downloadUrl = "https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe"                          
      }                                                                                                              
                                                                                                                     
      $candidates = Get-PythonCandidates -RepoRoot $RepoRoot                                                         
      foreach ($candidate in $candidates) {                                                                          
          if (Test-PythonCandidate -Path $candidate.Path -Args $candidate.Args) {                                   
              return $candidate                                                                                      
          }                                                                                                          
      }                                                                                                              
                                                                                                                     
      Write-Status "Python 3.11+ not found. Attempting automatic installation..." Yellow                             
      $installedCandidate = Install-PythonRuntime -DownloadUrl $downloadUrl
      if ($installedCandidate -and (Test-PythonCandidate -Path $installedCandidate.Path -Args $installedCandidate.Args)) {
          return $installedCandidate
      }

      $candidates = Get-PythonCandidates -RepoRoot $RepoRoot                                                         
      foreach ($candidate in $candidates) {                                                                          
          if (Test-PythonCandidate -Path $candidate.Path -Args $candidate.Args) {                                   
              return $candidate                                                                                      
          }                                                                                                         
      }                                                                                                             
                                                                                                                    
      throw "Python 3.11 or newer was not found after automatic installation."                                      
  }                                                                                                                 
                                                                                                                    
  function Read-ExitPrompt {                                                                                        
      param([string]$Message = "Press Enter to close this window...")                                               
      Write-Host ""                                                                                                 
      Write-Host $Message -ForegroundColor Yellow                                                                   
      try { [void][Console]::ReadLine() } catch { Read-Host | Out-Null }                                            
  }                                                                                                                 
                                                                                                                    
  $scriptDir = Split-Path -Parent $PSCommandPath                                                                    
  $repoRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path                                                       
                                                                                                                    
  if (-not (Test-IsAdmin)) {                                                                                        
      Write-Status "Requesting administrative privileges..." Yellow
      $argList = @(                                                                                                 
          "-NoLogo","-NoProfile",                                                                                   
          "-ExecutionPolicy","Bypass",                                                                              
          "-File","`"$PSCommandPath`"",                                                                             
          "-Elevated"                                                                                               
      )                                                                                                             
      Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $argList                                   
      exit                                                                                                          
  }                                                                                                                 
                                                                                                                    
  $logRoot = Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "Financial Command Center"            
  New-Item -ItemType Directory -Path $logRoot -Force | Out-Null                                                     
  $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"                                                                   
  $logPath = Join-Path $logRoot ("bootstrap-$timestamp.log")                                                        
  $transcriptStarted = $false                                                                                       
  $success = $false                                                                                                 
                                                                                                                    
  try {                                                                                                             
      Start-Transcript -Path $logPath -Force | Out-Null                                                             
      $transcriptStarted = $true                                                                                    
      Write-Status "Transcript started. Log file: $logPath" Cyan                                                    
                                                                                                                    
      Set-Location $repoRoot                                                                                        
      Write-Status "Working directory: $repoRoot" Gray                                                              
                                                                                                                    
      $python = Ensure-Python -RepoRoot $repoRoot                                                                   
      $pythonArgs = @()                                                                                             
      if ($python.Args) { $pythonArgs += $python.Args }                                                             
      Write-Status ("Using Python interpreter: {0}" -f $python.Path) Cyan                                           

      $bootstrapArgs = @("-m","bootstrap","install","--no-launch")                                                  
      Write-Status "Running bootstrap installer..." Cyan                                                            
      & $python.Path @pythonArgs @bootstrapArgs                                                                     
      if ($LASTEXITCODE -ne 0) {                                                                                    
          throw "Bootstrap CLI exited with code $LASTEXITCODE"                                                      
      }                                                                                                             
                                                                                                                    
      Write-Status "Installation complete." Green                                                                   
      Write-Status "Log saved to: $logPath" Green
      $success = $true                                                                                              
  } catch {                                                                                                         
      Write-Error $_                                                                                                
      Write-Status "Bootstrap failed. See log file for details: $logPath" Yellow                                    
      $success = $false                                                                                             
  } finally {
      if ($transcriptStarted) {                                                                                     
          try { Stop-Transcript | Out-Null } catch {}                                                               
      }                                                                                                             
                                                                                                                    
    if (-not $success) {
        Read-ExitPrompt
    } else {
        Write-Status "You may close this window." Gray
    }
}

if ($success) {
    exit 0
}

exit 1
