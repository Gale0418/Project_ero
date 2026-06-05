$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "model_install_utils.ps1")

$webuiRoot = "D:\AI\webui"
$waiTarget = Join-Path $webuiRoot "models\Stable-diffusion\waiIllustriousSDXL_v160.safetensors"

Install-HuggingFaceModel `
    -Name "WAI Illustrious SDXL v16.0 (adult trial checkpoint)" `
    -Url "https://huggingface.co/nyanpoko/public/resolve/c14aa2dd4a1e2946ce5a6f341731942a2c92a94d/waiNSFWIllustrious_v160.safetensors" `
    -Destination $waiTarget `
    -ExpectedBytes 6938040682 `
    -ExpectedSha256 "a5f58eb1c33616c4f06bca55af39876a7b817913cd829caa8acb111b770c85cc"

Write-Host ""
Write-Host "Trial Illustrious model installed. Refresh checkpoints in Forge before selecting it."
Write-Host "Note: this is an adult-capable trial model, not the reviewed DLsite commercial baseline."
