# Sammakorn live flood-context readout

- centre: 13.758235, 100.676084 (ARAYA office, หมู่บ้านสัมมากร สะพานสูง)
- radius: 5.0 km
- generated (UTC): 2026-09-26T05:37:47.471012+00:00
- as-of date: 2026-09-26
- sources used this run: bma_pumphistory, dds_daily_pdf, dds_flood_report, dds_tide_pdf, thaiwater_canal_waterlevel, thaiwater_flood_road

**อ่านตารางนี้อย่างไร**: ทุกแถวมี tag -- **MEASURED** = official_telemetry (หน่วยงานวัดเองด้วยเซนเซอร์ ไม่ผ่านคนคอมไพล์), **RELAYED** = official_report/compiled bulletin figure ที่ pipeline นี้ relay ต่อมา ตรง ๆ ไม่ใช่ของ pipeline นี้เอง, **STALE** = ค่าเก่ากว่าเกณฑ์ freshness (ดู `age_h` ใน JSON) -- แสดงไว้ ไม่ได้ตัดทิ้ง, **INSTINCT** = engineering judgment call ที่ยังไม่ verified (เช่น การจับคู่ candidate ระหว่างแหล่งข้อมูลโดยชื่อ ไม่ใช่ยืนยันว่าเป็นสถานีเดียวกันจริง), **OPEN** = ยังไม่มีข้อมูล. tag เหล่านี้บอกชั้นความน่าเชื่อถือ (`trust_tier` เต็ม ๆ อยู่ที่ `sources/registry.yaml`), ไม่ใช่คะแนนความเสี่ยง. **ไม่มีสูตรหรือคะแนนความเสี่ยงใด ๆ ในเอกสารนี้** (ตามกฎ equation discipline ของ workspace นี้) -- ทุกค่าคือค่าที่ relay/วัดมาตรง ๆ.

## 1. ฝน (Rain)
**MEASURED**
| station | value | unit | status | observed_at_utc | source | tag |
|---|---|---|---|---|---|---|
| ถ.เทศบาลสงเคราะห เขตจตุจักร | 210.00 | mm | - | 2026-09-26T00:00:00+00:00 | dds_daily_pdf | MEASURED |
| ศูนยราชการ-ถ.แจงวัฒนะ เขตหลักสี่ | 201.50 | mm | - | 2026-09-26T00:00:00+00:00 | dds_daily_pdf | MEASURED |
| ส.คลองเจาคุณสิงห เขตวังทองหลาง | 205.00 | mm | - | 2026-09-26T00:00:00+00:00 | dds_daily_pdf | MEASURED |
| สำนักการระบายน้ำ เขตดินแดง | 168.50 | mm | - | 2026-09-26T00:00:00+00:00 | dds_daily_pdf | MEASURED |
| สำนักงานเขตพญาไท | 203.00 | mm | - | 2026-09-26T00:00:00+00:00 | dds_daily_pdf | MEASURED |
| สำนักงานเขตสะพานสูง | 203.50 | mm | - | 2026-09-26T00:00:00+00:00 | dds_daily_pdf | MEASURED |

- **MISSING [OPEN]** The bulletin's own 24h weather FORECAST is free-text prose, not a structured figure this pipeline parses into a row -- see the 'weather_forecast' document instead of a table row here.

## 2. น้ำเหนือ (Chao Phraya inflow)
**MEASURED**
| station | variable | value | unit | status | observed_at_utc | source | tag |
|---|---|---|---|---|---|---|---|
| RID_CHAOPHRAYA | qmax_chaophraya_dam_cms | 690.00 | cms | - | 2026-09-19T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_nakhonsawan_cms | 1108.00 | cms | - | 2026-09-19T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_rama6_dam_cms | 176.00 | cms | - | 2026-09-19T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_samkhok_cms | 615.00 | cms | - | 2026-09-19T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_chaophraya_dam_cms | 990.00 | cms | - | 2026-09-20T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_nakhonsawan_cms | 1377.00 | cms | - | 2026-09-20T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_rama6_dam_cms | 169.00 | cms | - | 2026-09-20T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_samkhok_cms | 788.00 | cms | - | 2026-09-20T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_chaophraya_dam_cms | 1300.00 | cms | - | 2026-09-21T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_nakhonsawan_cms | 1611.00 | cms | - | 2026-09-21T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_rama6_dam_cms | 155.00 | cms | - | 2026-09-21T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_samkhok_cms | 989.00 | cms | - | 2026-09-21T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_chaophraya_dam_cms | 1620.00 | cms | - | 2026-09-22T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_nakhonsawan_cms | 1737.00 | cms | - | 2026-09-22T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_rama6_dam_cms | 146.00 | cms | - | 2026-09-22T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_samkhok_cms | 1184.00 | cms | - | 2026-09-22T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_chaophraya_dam_cms | 1750.00 | cms | - | 2026-09-23T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_nakhonsawan_cms | 1777.00 | cms | - | 2026-09-23T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_rama6_dam_cms | 149.00 | cms | - | 2026-09-23T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_samkhok_cms | 1375.00 | cms | - | 2026-09-23T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_chaophraya_dam_cms | 1750.00 | cms | - | 2026-09-24T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_nakhonsawan_cms | 1795.00 | cms | - | 2026-09-24T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_rama6_dam_cms | 173.00 | cms | - | 2026-09-24T17:00:00+00:00 | dds_daily_pdf | MEASURED |
| RID_CHAOPHRAYA | qmax_samkhok_cms | 1693.00 | cms | - | 2026-09-24T17:00:00+00:00 | dds_daily_pdf | MEASURED |

- **MISSING [OPEN]** Report-date Chao Phraya row is incomplete in the bulletin, raw text preserved verbatim, not parsed: 26 ก.ย. 69: 26 ก.ย. 69           1,827           1,850                       1,748                                                                       19.25       +1.01

## 3. น้ำทะเลหนุน (Tide surge)
**OFFICIAL FORECAST**
| station | variable | value | unit | observed_at_utc | source | tag |
|---|---|---|---|---|---|---|
| NAVY_HYDRO (bulletin sec.7) | tide_ขึ้นเต็มที่_am_m | 0.66 | m | 2026-09-26T00:00:00+00:00 | dds_daily_pdf | RELAYED |
| NAVY_HYDRO (bulletin sec.7) | tide_ลงเต็มที่_am_m | -0.05 | m | 2026-09-26T00:00:00+00:00 | dds_daily_pdf | RELAYED |
| ฐานน้ำทะเลหนุน (bulletin sec.5, RID/Navy) | tide_base_level_m | 0.95 | m | 2026-09-19T17:00:00+00:00 | dds_daily_pdf | RELAYED |
| ฐานน้ำทะเลหนุน (bulletin sec.5, RID/Navy) | tide_base_level_m | 0.95 | m | 2026-09-20T17:00:00+00:00 | dds_daily_pdf | RELAYED |
| ฐานน้ำทะเลหนุน (bulletin sec.5, RID/Navy) | tide_base_level_m | 1.10 | m | 2026-09-21T17:00:00+00:00 | dds_daily_pdf | RELAYED |
| ฐานน้ำทะเลหนุน (bulletin sec.5, RID/Navy) | tide_base_level_m | 1.13 | m | 2026-09-22T17:00:00+00:00 | dds_daily_pdf | RELAYED |
| ฐานน้ำทะเลหนุน (bulletin sec.5, RID/Navy) | tide_base_level_m | 1.10 | m | 2026-09-23T17:00:00+00:00 | dds_daily_pdf | RELAYED |
| ฐานน้ำทะเลหนุน (bulletin sec.5, RID/Navy) | tide_base_level_m | 1.06 | m | 2026-09-24T17:00:00+00:00 | dds_daily_pdf | RELAYED |
| NAVY_HYDRO_HQ (monthly tide table) | tide_hw_am_level_m | 0.66 | m | 2026-09-25T23:32:00+00:00 | dds_tide_pdf | RELAYED |
| NAVY_HYDRO_HQ (monthly tide table) | tide_hw_pm_level_m | 1.01 | m | 2026-09-26T12:25:00+00:00 | dds_tide_pdf | RELAYED |
| NAVY_HYDRO_HQ (monthly tide table) | tide_lw_am_level_m | -0.05 | m | 2026-09-25T18:26:00+00:00 | dds_tide_pdf | RELAYED |
| NAVY_HYDRO_HQ (monthly tide table) | tide_lw_pm_level_m | -0.43 | m | 2026-09-26T06:25:00+00:00 | dds_tide_pdf | RELAYED |


## 4. การระบาย (Drainage: canals + pumps)
**MEASURED**
| station | value | unit | status | observed_at_utc | source | tag |
|---|---|---|---|---|---|---|
| ค.หัวหมาก ถ.ศรีนครินทร์ | 0.46 | m | CRITICAL | 2026-09-25T13:05:00+00:00 | thaiwater_canal_waterlevel | MEASURED |
| ค.กะจะ ถ.พระราม 9 ซ.57 | 0.16 | m | CRITICAL | 2026-09-25T13:05:00+00:00 | thaiwater_canal_waterlevel | MEASURED |
| ค.จิก ถ.หัวหมาก | 0.00 | m | CRITICAL | 2026-09-25T13:05:00+00:00 | thaiwater_canal_waterlevel | MEASURED |
| ค.ลาดบัวขาว ถ.เคหะร่มเกล้า | 0.75 | m | CRITICAL | 2026-09-25T13:05:00+00:00 | thaiwater_canal_waterlevel | MEASURED |
| ค.ลาดบัวขาว ซ.กาญจนาภิเษก 24 | 0.71 | m | CRITICAL | 2026-09-25T13:05:00+00:00 | thaiwater_canal_waterlevel | MEASURED |
| ปตร.คลองประเวศฯ-วัดกระทุ่มฯ | 0.58 | m | CRITICAL | 2026-09-25T13:05:00+00:00 | thaiwater_canal_waterlevel | MEASURED |
| ค.แสนแสบ-สนข.บางกะปิ | 0.40 | m | WATCH | 2026-09-25T13:05:00+00:00 | thaiwater_canal_waterlevel | MEASURED |
| ค.แสนแสบ-เสรีไทย 24 | -0.21 | m | NORMAL | 2026-09-25T13:05:00+00:00 | thaiwater_canal_waterlevel | MEASURED |
| ค.ตาพุก ค.ทับช้างบน | 0.71 | m | CRITICAL | 2026-09-25T13:05:00+00:00 | thaiwater_canal_waterlevel | MEASURED |
| ค.ยายเผื่อน ถ.ลาดพร้าว | -0.21 | m | NORMAL | 2026-09-25T13:05:00+00:00 | thaiwater_canal_waterlevel | MEASURED |
| ค.ยายเผื่อน แฮปปี้แลนด์ | 0.18 | m | OVERBANK | 2026-09-25T13:00:00+00:00 | thaiwater_canal_waterlevel | MEASURED |
| ค.ศาลาลอย ถ.อ่อนนุช 61 | 0.23 | m | CRITICAL | 2026-09-25T09:00:00+00:00 | thaiwater_canal_waterlevel | MEASURED |
| ค.ตาหนัง ถ.ลาดพร้าว | -2.00 | m | NORMAL | 2026-06-09T05:10:00+00:00 | thaiwater_canal_waterlevel | STALE |
| คลองแสนแสบช่วง ซ.เสรีไทย 24 เขตบึงกุ่ม | -0.34 | m | NO_THRESHOLD | 2019-12-24T07:38:00+00:00 | thaiwater_canal_waterlevel | STALE |
| สถานีสูบน้ำคลองซอยระหัส 1 ตอนถนนสหกรณ์สาย 1 | 0.99 | m | ปกติ | 2026-09-26T05:00:00+00:00 | bma_pumphistory | MEASURED |
| สถานีสูบน้ำลำรางสาธารณะ (ตอนคลองบางเตย นวมินทร์ 26) | 0.44 | m | ปกติ | 2026-09-26T05:00:00+00:00 | bma_pumphistory | MEASURED |
| สถานีสูบน้ำบึงกุ่ม (ตอนคลองบางเตย) | 0.89 | m | ปกติ | 2026-09-26T05:00:00+00:00 | bma_pumphistory | MEASURED |
| สถานีสูบน้ำคลองจิต | -1.12 | m | ปกติ | 2026-09-26T05:00:00+00:00 | bma_pumphistory | MEASURED |
| สถานีสูบน้ำคลองโต๊ะยอ | 1.18 | m | ปกติ | 2026-09-26T05:00:00+00:00 | bma_pumphistory | MEASURED |
| สถานีสูบน้ำคลองศาลาลอยบน (ตอนอ่อนนุช) | 0.64 | m | ปกติ | 2026-09-26T05:00:00+00:00 | bma_pumphistory | MEASURED |
| สถานีสูบน้ำคลองศาลาลอยล่าง (ตอนอ่อนนุช) | 0.60 | m | ปกติ | 2026-09-26T05:00:00+00:00 | bma_pumphistory | MEASURED |
| สถานีสูบน้ำจระเข้ขบ (ตอนอ่อนนุช) | 0.79 | m | ปกติ | 2026-09-26T05:00:00+00:00 | bma_pumphistory | MEASURED |
| สถานีสูบน้ำคลองบ้านม้า 2 | 0.00 | m | ขัดข้อง | 2026-09-26T05:00:00+00:00 | bma_pumphistory | MEASURED |
| สถานีสูบน้ำบึงที่ 4 ตอนคลองวัดใหญ่ | 0.73 | m | ปกติ | 2026-09-26T05:00:00+00:00 | bma_pumphistory | MEASURED |
| สถานีสูบน้ำบึงที่ 2 ตอนคลองบ้านม้า 2 | 0.57 | m | ปกติ | 2026-09-26T05:00:00+00:00 | bma_pumphistory | MEASURED |
| สถานีสูบน้ำบึงที่ 1 ตอนคลองสะพานสูง | 0.00 | m | ขัดข้อง | 2026-09-26T05:00:00+00:00 | bma_pumphistory | MEASURED |
| คลองทวีวัฒนาตัดคลองภาษีเจริญ | 1.00 | m | ระดับน้ำวิกฤติ | 2026-09-26T00:00:00+00:00 | dds_daily_pdf | MEASURED |
| คลองลาดพราว 56 | 0.95 | m | ระดับน้ำวิกฤติ | 2026-09-26T00:00:00+00:00 | dds_daily_pdf | MEASURED |
| คลองเปรมประชากร (ตอนคลองบานใหม) | 1.55 | m | ระดับน้ำวิกฤติ | 2026-09-26T00:00:00+00:00 | dds_daily_pdf | MEASURED |
| คลองแสนแสบ-คลองตัน (แสนแสบเกา) | 0.55 | m | ระดับน้ำวิกฤติ | 2026-09-26T00:00:00+00:00 | dds_daily_pdf | MEASURED |
| คลองแสนแสบ-เขตบางกะป | 0.40 | m | ระดับน้ำวิกฤติ | 2026-09-26T00:00:00+00:00 | dds_daily_pdf | MEASURED |
| ปตร.คลองทวีวัฒนา (ดานใน) | 1.15 | m | ระดับน้ำวิกฤติ | 2026-09-26T00:00:00+00:00 | dds_daily_pdf | MEASURED |
| ปตร.คลองประเวศฯ-ลาดกระบัง | 0.82 | m | ระดับน้ำวิกฤติ | 2026-09-26T00:00:00+00:00 | dds_daily_pdf | MEASURED |
| ปตร.คลองมหาสวัสดิ์-ฉิมพลี (ดานแมน้ำ) | 1.38 | m | ระดับน้ำปกติ | 2026-09-26T00:00:00+00:00 | dds_daily_pdf | MEASURED |
| ปตร.คลองสองสายใต | 1.92 | m | ระดับน้ำวิกฤติ | 2026-09-26T00:00:00+00:00 | dds_daily_pdf | MEASURED |
| ปตร.คลองแสนแสบ-มีนบุรี.80 | 1.09 | m | ระดับน้ำวิกฤติ | 2026-09-26T00:00:00+00:00 | dds_daily_pdf | MEASURED |

- **MISSING [OPEN]** No pump-on/off or gate-open/shut FORECAST exists anywhere in these sources -- BMA PumpHistory gives current status only (MEASURED, above), the DDS daily bulletin has no drainage forecast section.

## 5. ถนนน้ำท่วม (Flood-affected roads)
**MEASURED**
| station | value | unit | status | observed_at_utc | source | tag |
|---|---|---|---|---|---|---|
| ถ.พัฒนาการ แยกศรีนครินทร์ | 6.30 | cm | - | 2026-09-25T13:10:00+00:00 | thaiwater_flood_road | MEASURED |
| ถ.นวมินทร์ ช่วง ซ.นวมินทร์ 38 * | 20.00 | cm | asterisk-flagged, meaning unconfirmed [OPEN] | 2026-09-25T13:05:00+00:00 | thaiwater_flood_road | MEASURED |
| ถ.นวมินทร์ ช่วงแยกบางกะปิ * | 20.00 | cm | asterisk-flagged, meaning unconfirmed [OPEN] | 2026-09-25T13:05:00+00:00 | thaiwater_flood_road | MEASURED |
| ถ.นวมินทร์ ช่วงตรงข้ามสถานีตำรวจนครบาลลาดพร้าว * | 20.00 | cm | asterisk-flagged, meaning unconfirmed [OPEN] | 2026-09-25T13:05:00+00:00 | thaiwater_flood_road | MEASURED |
| ถ.อ่อนนุช ช่วง ซ.อ่อนนุช 59 * | 20.00 | cm | asterisk-flagged, meaning unconfirmed [OPEN] | 2026-09-25T13:05:00+00:00 | thaiwater_flood_road | MEASURED |
| ถ.ศรีนครินทร์ ช่วง ถ.กำแพงเพชร 7 * | 20.00 | cm | asterisk-flagged, meaning unconfirmed [OPEN] | 2026-09-25T13:05:00+00:00 | thaiwater_flood_road | MEASURED |
| ถ.พัฒนาการ ช่วง ซ.พัฒนาการ 53 * | 10.00 | cm | asterisk-flagged, meaning unconfirmed [OPEN] | 2026-09-25T13:05:00+00:00 | thaiwater_flood_road | MEASURED |

- **MISSING [OPEN]** The '*' suffix seen on some road names in the raw feed, and its exact-20.0/exact-10.0 values, are relayed as-is -- their meaning was never confirmed against BMA/thaiwater documentation.

## โหนดของสัมมากร (Sammakorn's own nodes)
### north (แสนแสบ)
| station_code | name | value_m | status | dist_km | observed_at_utc | tag |
|---|---|---|---|---|---|---|
| WL.SSB.07 | ค.แสนแสบ-สนข.บางกะปิ | 0.40 | WATCH | 3.14 | 2026-09-25T13:05:00+00:00 | MEASURED |
| WL.SSB.08 | ค.แสนแสบ-เสรีไทย 24 | -0.21 | NORMAL | 2.49 | 2026-09-25T13:05:00+00:00 | MEASURED |

### south
| station_code | name | value_m | status | dist_km | observed_at_utc | tag |
|---|---|---|---|---|---|---|
| WL.TPK.03 | ค.ตาพุก ค.ทับช้างบน | 0.71 | CRITICAL | 3.96 | 2026-09-25T13:05:00+00:00 | MEASURED |
| WL.PWT.03 | ปตร.คลองประเวศฯ-วัดกระทุ่มฯ | 0.58 | CRITICAL | 4.08 | 2026-09-25T13:05:00+00:00 | MEASURED |
| WL.HMK.01 | ค.หัวหมาก ถ.ศรีนครินทร์ | 0.46 | CRITICAL | 4.70 | 2026-09-25T13:05:00+00:00 | MEASURED |

### in-basin pumps (ST.SPS)
| station_code | name | level_m | pumps_on | pumps_total | gate_open_m | status | dist_km | observed_at_utc | tag |
|---|---|---|---|---|---|---|---|---|---|
| ST.SPS.01 | สถานีสูบน้ำคลองบ้านม้า 2 | 0.00 | 0 | 4 | 0.00 | ขัดข้อง | 2.07 | 2026-09-26T05:00:00+00:00 | MEASURED |
| ST.SPS.02 | สถานีสูบน้ำบึงที่ 4 ตอนคลองวัดใหญ่ | 0.73 | 0 | 2 | 0.00 | ปกติ | 0.48 | 2026-09-26T05:00:00+00:00 | MEASURED |
| ST.SPS.03 | สถานีสูบน้ำบึงที่ 2 ตอนคลองบ้านม้า 2 | 0.57 | 1 | 3 | - | ปกติ | 0.98 | 2026-09-26T05:00:00+00:00 | MEASURED |
| ST.SPS.04 | สถานีสูบน้ำบึงที่ 1 ตอนคลองสะพานสูง | 0.00 | 0 | 2 | - | ขัดข้อง | 1.43 | 2026-09-26T05:00:00+00:00 | MEASURED |

## ความขัดแย้งระหว่างแหล่ง (Cross-source contradictions -- not resolved)
- **canal_level_same_name_candidate**: dds_daily_pdf=0.82 (2026-09-26T00:00:00+00:00) vs thaiwater_canal_waterlevel=0.68 (2026-09-25T13:05:00+00:00) -- CANDIDATE pairing by exact normalized-name match only (no coordinate/code crosswalk available for the DDS row) -- 'ปตร.คลองประเวศฯ-ลาดกระบัง' (DDS bulletin) vs 'ปตร.คลองประเวศฯ-ลาดกระบัง' (thaiwater) -- 0.14 m apart, observations ~10.9h apart -- NOT verified as the same physical station, not resolved.

## สิ่งที่ยังขาด (Open / missing)
- **[OPEN] governor_shared_flooded_roads**: Registered in sources/registry.yaml but not yet imported (manual-import source, no fetcher by design) -- cannot cross-check against it yet.
- **[OPEN] bma_klongmap**: Still HTTP 403 as of the last check -- parser stays ready, dormant.
- **[OPEN] pages 4-6 of the DDS daily PDF**: Raster images (weather map, satellite photo, rain-distribution maps, 7-day forecast chart) -- zero extractable text, not covered without OCR.
- **[OPEN] dds_nowcast_gif**: Stored as an image snapshot only, never parsed -- no numeric reading comes from this source.
- **[OPEN] rtsd_2010_ground_level_map / rid_flood_risk_map**: Static reference assets, not wired into observations/documents yet.

## ภาพรวม (Overall picture -- [INSTINCT], ไม่ใช่คะแนน/ไม่ใช่การพยากรณ์)
- สถานะที่แต่ละหน่วยงานประกาศเองสำหรับสถานีในรัศมี 5.0 km (26 reading(s)): CRITICAL=8, NORMAL=3, NO_THRESHOLD=1, OVERBANK=1, WATCH=1, ขัดข้อง=2, ปกติ=10. นี่คือการนับสถานะที่หน่วยงานต้นทางตั้งไว้เอง (warning/critical/bank ของแต่ละสถานี) ไม่ใช่คะแนนหรือการจัดอันดับของ pipeline นี้.
- 2 แถวใน 'การระบาย' เป็นค่าเก่ากว่า 24 ชั่วโมง (tag STALE) -- ยังแสดงไว้เพื่อความโปร่งใส แต่ไม่ควรอ่านเป็นสถานการณ์ปัจจุบัน.
- พบ 1 รายการที่แหล่งข้อมูลไม่ตรงกัน (ดู 'ความขัดแย้งระหว่างแหล่ง' ด้านล่าง) -- หน่วยงานไทยหลายหน่วยงานทำงานแข่งกันและข้อมูลไม่สอดคล้องกัน (project ruling) -- ไม่ resolve ให้ว่าใครถูก, ผู้อ่านต้องชั่งน้ำหนักเอง.
- ใช้ข้อมูลจาก 6 แหล่งในรอบนี้: bma_pumphistory, dds_daily_pdf, dds_flood_report, dds_tide_pdf, thaiwater_canal_waterlevel, thaiwater_flood_road. แต่ละแหล่งมี trust_tier ของตัวเอง (official_telemetry / official_report / official_shared_inference) -- ดูรายละเอียดที่ sources/registry.yaml, ไม่ได้ย่อยลงมา เป็นค่าเดียวที่นี่.
