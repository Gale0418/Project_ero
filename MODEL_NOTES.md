# Project_ero 模型備忘錄

更新日期：2026-06-03

## 目前管線

| 用途 | 本機模型 | 判斷 |
| --- | --- | --- |
| 草稿結構 | `autismmixSDXL_autismmixPony.safetensors` | 保留作姿勢探索器。正式 Story 模式只將草稿送進 ControlNet，不再把草稿當 img2img 底圖。 |
| 完稿畫風 | `animagine-xl-4.0-opt.safetensors` | 正式基準，已安裝並通過 SHA256。官方模型卡明確允許商業使用，並針對穩定性、人體比例與 prompt adherence 優化。 |
| 姿勢固定 | `xinsir-openpose-sdxl-1.0.safetensors` | 正式基準，已下載並通過 SHA256，等待將 `.part` 提升為正式檔名。官方頁標示 Apache-2.0，公開評測 mAP `0.357`。 |
| 舊姿勢固定 | `openposeSDXL_v10 [f4251cb4]` | 保留作 fallback。此 hash 對應 2023 年的 `OpenPoseXL2` / thibaud SDXL OpenPose，公開評測 mAP `0.209`。 |
| 成人向試驗 | `waiIllustriousSDXL_v160.safetensors` | 高評價 Illustrious 系 checkpoint，僅作本機 A/B 與成人向提示相容性測試；不列入 DLsite 商用基準。 |

## 建議順序

1. 保留現有 Pony 草稿模型，讓既有姿勢探索流程穩定運作。
2. Story 正式輸出使用 `controlnet_txt2img`：只傳姿勢控制資訊，不繼承 Pony 草稿像素。
3. 完稿先以 [`cagliostrolab/animagine-xl-4.0`](https://huggingface.co/cagliostrolab/animagine-xl-4.0) 的 `4.0 Opt` 版本作可商用基準。
4. OpenPose 升級為 [`xinsir/controlnet-openpose-sdxl-1.0`](https://huggingface.co/xinsir/controlnet-openpose-sdxl-1.0)。
5. 若要進一步壓低中間素材授權風險，將 Pony 草稿替換成自行製作或授權清楚的 pose 圖。

## 可商用候選

| 模型 | 官方授權資訊 | 用途與結論 |
| --- | --- | --- |
| [`cagliostrolab/animagine-xl-4.0`](https://huggingface.co/cagliostrolab/animagine-xl-4.0) | CreativeML Open RAIL++-M；官方模型卡明寫允許商業使用、修改與散布 | 已選為正式完稿基準。`4.0 Opt` 改善人體比例、穩定性與雜訊。 |
| [`OnomaAIResearch/Illustrious-XL-v2.0`](https://huggingface.co/OnomaAIResearch/Illustrious-XL-v2.0) | Hugging Face 標示 CreativeML Open RAIL-M | 可作下一顆 A/B 候選。先不下載，避免同時更換太多變因。 |
| [`stabilityai/stable-diffusion-xl-base-1.0`](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0) | CreativeML Open RAIL++-M | 授權基準乾淨，但動畫畫風不是專長，保留作基礎模型參考。 |

## 成人向試驗候選

| 模型 | 來源資訊 | 用途與結論 |
| --- | --- | --- |
| [`WAI-illustrious-SDXL v16.0`](https://civitaiarchive.com/models/827184?modelVersionId=2514310) | Civitai 頁面標示 Illustrious License、SafeTensor、Base Model Illustrious；CivArchive 記錄 `231,290` downloads、SHA256 `a5f58eb1c33616c4f06bca55af39876a7b817913cd829caa8acb111b770c85cc`。Hugging Face mirror 的 LFS pointer bytes 與 SHA256 相同。 | 下載到 WebUI checkpoint 目錄作成人向測試與風格比較。授權條款不夠乾淨，不能直接當付費發布基準。 |

安裝或續傳此試驗模型：

```powershell
pwsh -File tools/install_trial_illustrious_models.ps1
```

## DLsite 販售前授權閘門

[`Laxhar/noobai-XL-1.0`](https://huggingface.co/Laxhar/noobai-XL-1.0) 的官方模型卡明確列出商業禁止條款，包含模型生成產品。NoobAI 衍生 checkpoint 是否能用於付費 DLsite 作品，必須逐顆核對來源頁、授權繼承與使用條款。

[`PurpleSmartAI/Pony-Diffusion-V6-XL`](https://huggingface.co/PurpleSmartAI/Pony-Diffusion-V6-XL) 的官方頁面標示為 modified Fair AI Public License，商業使用需聯絡作者。技術上改成 pose-only 可避免直接繼承草稿像素，但不等於自動取得法律保證。

在授權稽核完成前，NoobAI 系模型不作 DLsite 正式素材來源；Pony 系僅作姿勢探索中間工具。這是工程風險控管，不是法律意見。
