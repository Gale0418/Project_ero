$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "model_install_utils.ps1")

$webuiRoot = "D:\AI\webui"
$animagineTarget = Join-Path $webuiRoot "models\Stable-diffusion\animagine-xl-4.0-opt.safetensors"
$openposeTarget = Join-Path $webuiRoot "models\ControlNet\xinsir-openpose-sdxl-1.0.safetensors"

Install-HuggingFaceModel `
    -Name "Animagine XL 4.0 Opt" `
    -Url "https://huggingface.co/cagliostrolab/animagine-xl-4.0/resolve/main/animagine-xl-4.0-opt.safetensors" `
    -Destination $animagineTarget `
    -ExpectedBytes 6938350040 `
    -ExpectedSha256 "6327eca98bfb6538dd7a4edce22484a1bbc57a8cff6b11d075d40da1afb847ac"

Install-HuggingFaceModel `
    -Name "xinsir OpenPose SDXL 1.0" `
    -Url "https://huggingface.co/xinsir/controlnet-openpose-sdxl-1.0/resolve/main/diffusion_pytorch_model.safetensors" `
    -Destination $openposeTarget `
    -ExpectedBytes 2502139104 `
    -ExpectedSha256 "b8524e557a7df60d081f5d4a0eb109967d107df217943bf88c2d99b9ebcc06c5"

Write-Host ""
Write-Host "Models installed. Refresh checkpoints in Forge, then restart Forge if the new ControlNet model is not listed."
