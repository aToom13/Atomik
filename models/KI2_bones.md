# KI2.vrm Model Kemik ve Mesh Yapısı

Bu dosya, `models/KI2.vrm` VRM modelindeki tüm kemikleri, mesh'leri ve objeleri içerir.

---

## 📦 İsimlendirme Kuralları

VRM standartı kemik isimlendirme:
- `J_Bip_` = Ana vücut kemikleri (Biped)
- `J_Opt_` = Opsiyonel kemikler (kuyruk, kulaklar, gözlük vb.)
- `J_Sec_` = İkincil animasyon kemikleri (saç, kıyafet vb.)
- `_C_` = Center (merkez)
- `_L_` = Left (sol)
- `_R_` = Right (sağ)

---

## 🦴 Ana Vücut Kemikleri (Biped)

### Omurga ve Gövde
| Kemik                | Açıklama                     |
| -------------------- | ---------------------------- |
| `Root`               | Kök kemik                    |
| `J_Bip_C_Hips`       | Kalça (tüm vücudun ebeveyni) |
| `J_Bip_C_Spine`      | Alt omurga                   |
| `J_Bip_C_Chest`      | Göğüs                        |
| `J_Bip_C_UpperChest` | Üst göğüs                    |
| `J_Bip_C_Neck`       | Boyun                        |
| `J_Bip_C_Head`       | Kafa                         |

### Sol Kol ve El
| Kemik              | Açıklama             |
| ------------------ | -------------------- |
| `J_Bip_L_Shoulder` | Sol omuz             |
| `J_Bip_L_UpperArm` | Sol üst kol          |
| `J_Bip_L_LowerArm` | Sol ön kol           |
| `J_Bip_L_Hand`     | Sol el               |
| `J_Bip_L_Thumb1`   | Sol başparmak 1      |
| `J_Bip_L_Thumb2`   | Sol başparmak 2      |
| `J_Bip_L_Thumb3`   | Sol başparmak 3      |
| `J_Bip_L_Index1`   | Sol işaret parmağı 1 |
| `J_Bip_L_Index2`   | Sol işaret parmağı 2 |
| `J_Bip_L_Index3`   | Sol işaret parmağı 3 |
| `J_Bip_L_Middle1`  | Sol orta parmak 1    |
| `J_Bip_L_Middle2`  | Sol orta parmak 2    |
| `J_Bip_L_Middle3`  | Sol orta parmak 3    |
| `J_Bip_L_Ring1`    | Sol yüzük parmağı 1  |
| `J_Bip_L_Ring2`    | Sol yüzük parmağı 2  |
| `J_Bip_L_Ring3`    | Sol yüzük parmağı 3  |
| `J_Bip_L_Little1`  | Sol serçe parmak 1   |
| `J_Bip_L_Little2`  | Sol serçe parmak 2   |
| `J_Bip_L_Little3`  | Sol serçe parmak 3   |

### Sağ Kol ve El
| Kemik               | Açıklama           |
| ------------------- | ------------------ |
| `J_Bip_R_Shoulder`  | Sağ omuz           |
| `J_Bip_R_UpperArm`  | Sağ üst kol        |
| `J_Bip_R_LowerArm`  | Sağ ön kol         |
| `J_Bip_R_Hand`      | Sağ el             |
| `J_Bip_R_Thumb1-3`  | Sağ başparmak      |
| `J_Bip_R_Index1-3`  | Sağ işaret parmağı |
| `J_Bip_R_Middle1-3` | Sağ orta parmak    |
| `J_Bip_R_Ring1-3`   | Sağ yüzük parmağı  |
| `J_Bip_R_Little1-3` | Sağ serçe parmak   |

### Sol Bacak
| Kemik              | Açıklama            |
| ------------------ | ------------------- |
| `J_Bip_L_UpperLeg` | Sol üst bacak       |
| `J_Bip_L_LowerLeg` | Sol alt bacak       |
| `J_Bip_L_Foot`     | Sol ayak            |
| `J_Bip_L_ToeBase`  | Sol ayak parmakları |

### Sağ Bacak
| Kemik              | Açıklama            |
| ------------------ | ------------------- |
| `J_Bip_R_UpperLeg` | Sağ üst bacak       |
| `J_Bip_R_LowerLeg` | Sağ alt bacak       |
| `J_Bip_R_Foot`     | Sağ ayak            |
| `J_Bip_R_ToeBase`  | Sağ ayak parmakları |

---

## 🐈 Opsiyonel Kemikler (J_Opt_)

### Kuyruk (FoxTail) - 5 Segment
```
J_Opt_C_FoxTail1_01  (Kök - en az hareket)
  └── J_Opt_C_FoxTail2_01
       └── J_Opt_C_FoxTail3_01
            └── J_Opt_C_FoxTail4_01
                 └── J_Opt_C_FoxTail5_01 (Uç - en çok hareket)
                      └── J_Opt_C_FoxTail5_end_01
```

### Kedi Kulakları (CatEar)
**Sol Kulak:**
```
J_Opt_L_CatEar1_01 (Kök)
  └── J_Opt_L_CatEar2_01 (Orta)
       └── J_Opt_L_CatEar2_end_01 (Uç)
```

**Sağ Kulak:**
```
J_Opt_R_CatEar1_01 (Kök)
  └── J_Opt_R_CatEar2_01 (Orta)
       └── J_Opt_R_CatEar2_end_01 (Uç)
```

### Diğer Opsiyoneller
| Kemik                | Açıklama |
| -------------------- | -------- |
| `J_Opt_C_Glasses_01` | Gözlük   |

---

## 💇 İkincil Animasyon Kemikleri (J_Sec_)

### Saç Kemikleri
Saçlar segmentlere ayrılmış durumda. Her segment bir öncekinden devam eder.

**Sol Saç Telleri:**
- `J_Sec_Hair1_01` → `J_Sec_Hair2_01` → `J_Sec_Hair3_01`
- `J_Sec_Hair1_02` → `J_Sec_Hair2_02` 
- `J_Sec_Hair1_03` → `J_Sec_Hair2_03`
- `J_Sec_Hair1_04` → `J_Sec_Hair2_04` → `J_Sec_Hair3_04`
- `J_Sec_Hair1_05` → `J_Sec_Hair2_05` → `J_Sec_Hair3_05`
- `J_Sec_Hair1_06` → `J_Sec_Hair2_06`
- `J_Sec_Hair1_07` → `J_Sec_Hair2_07` → `J_Sec_Hair3_07`

### Göğüs 
| Kemik           | Açıklama    |
| --------------- | ----------- |
| `J_Sec_L_Bust1` | Sol göğüs 1 |
| `J_Sec_L_Bust2` | Sol göğüs 2 |
| `J_Sec_R_Bust1` | Sağ göğüs 1 |
| `J_Sec_R_Bust2` | Sağ göğüs 2 |

### Kapüşon
| Kemik                 | Açıklama          |
| --------------------- | ----------------- |
| `J_Sec_C_Hood`        | Ana kapüşon       |
| `J_Sec_L_HoodString1` | Sol kapüşon ipi 1 |
| `J_Sec_L_HoodString2` | Sol kapüşon ipi 2 |
| `J_Sec_R_HoodString1` | Sağ kapüşon ipi 1 |
| `J_Sec_R_HoodString2` | Sağ kapüşon ipi 2 |

### Kıyafet/Etek (CoatSkirt) - 5 Segment Her Biri

**Sol Taraf:**
| Konum | Kemikler                                                         |
| ----- | ---------------------------------------------------------------- |
| Arka  | `J_Sec_L_CoatSkirtBack` → `_01` → `_02` → `_03` → `_04` → `_05`  |
| Ön    | `J_Sec_L_CoatSkirtFront` → `_01` → `_02` → `_03` → `_04` → `_05` |
| Yan   | `J_Sec_L_CoatSkirtSide` → `_01` → `_02` → `_03` → `_04` → `_05`  |

**Sağ Taraf:**
| Konum | Kemikler                                                         |
| ----- | ---------------------------------------------------------------- |
| Arka  | `J_Sec_R_CoatSkirtBack` → `_01` → `_02` → `_03` → `_04` → `_05`  |
| Ön    | `J_Sec_R_CoatSkirtFront` → `_01` → `_02` → `_03` → `_04` → `_05` |
| Yan   | `J_Sec_R_CoatSkirtSide` → `_01` → `_02` → `_03` → `_04` → `_05`  |

---

## 🎭 Mesh'ler (Görsel Parçalar)

| Mesh                                 | Tip         | Açıklama                  |
| ------------------------------------ | ----------- | ------------------------- |
| `Face`                               | SkinnedMesh | Yüz geometrisi            |
| `Face_(merged)(Clone)baked_0` - `_5` | SkinnedMesh | Yüz materyal katmanları   |
| `Body`                               | SkinnedMesh | Vücut geometrisi          |
| `Body_(merged)baked_0` - `_17`       | SkinnedMesh | Vücut materyal katmanları |
| `Hair`                               | SkinnedMesh | Saç geometrisi            |

---

## 😊 VRM İfadeleri (Expressions/BlendShapes)

### Temel İfadeler
| İfade       | Kullanım |
| ----------- | -------- |
| `neutral`   | Nötr yüz |
| `happy`     | Mutlu 😊  |
| `angry`     | Kızgın 😠 |
| `sad`       | Üzgün 😢  |
| `relaxed`   | Rahat 😌  |
| `surprised` | Şaşkın 😲 |

### Dudak Senkronizasyonu (Lip Sync)
| İfade | Ses           |
| ----- | ------------- |
| `aa`  | Ağız açık (A) |
| `ih`  | İ sesi        |
| `ou`  | O/U sesi      |
| `ee`  | E sesi        |
| `oh`  | O sesi        |

### Göz Kırpma
| İfade        | Kullanım    |
| ------------ | ----------- |
| `blink`      | Her iki göz |
| `blinkLeft`  | Sol göz     |
| `blinkRight` | Sağ göz     |

### Bakış Yönü
| İfade       | Yön        |
| ----------- | ---------- |
| `lookUp`    | Yukarı bak |
| `lookDown`  | Aşağı bak  |
| `lookLeft`  | Sola bak   |
| `lookRight` | Sağa bak   |

---

## 🛠️ VRM Özel Objeler

| Obje             | Tip      | Açıklama                          |
| ---------------- | -------- | --------------------------------- |
| `secondary`      | Object3D | İkincil hareket konteyner         |
| `VRMHumanoidRig` | Object3D | Humanoid rig                      |
| `Normalized_*`   | Object3D | Normalize edilmiş kemik düğümleri |

---

## 📝 Animasyon için Önemli Notlar

1. **Kuyruk animasyonu:** `FoxTail` kemiklerini hedefle, segment numarasına göre hareket yoğunluğunu artır
2. **Kulak seğirmesi:** `CatEar` kemiklerini hedefle, `_L_` ve `_R_` ile sol/sağ ayır
3. **Saç fiziği:** `J_Sec_Hair` kemiklerini hedefle, segment numarasına göre cascading efekti
4. **Kıyafet fiziği:** `CoatSkirt` kemiklerini hedefle, Front/Back/Side için farklı davranış
5. **Yüz ifadeleri:** `vrm.expressionManager.setValue('ifade_adi', 0-1)` kullan

---

*Bu dosya otomatik olarak oluşturulmuştur. Model: KI2.vrm*
