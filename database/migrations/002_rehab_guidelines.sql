-- database/migrations/002_rehab_guidelines.sql
-- RAG临床指南库 — 循证康复指南（来源：公开可获取的临床指南和系统综述）
--
-- 数据来源说明：
--   膝关节置换术(TKA)：
--     • AAOS Clinical Practice Guideline: Surgical Management of Osteoarthritis of the Knee (2022)
--       https://www.aaos.org/smoak2cpg | 全文公开获取
--     • AAOS OrthoInfo: Total Knee Replacement Exercise Guide
--       https://orthoinfo.aaos.org/en/recovery/total-knee-replacement-exercise-guide/
--     • EORIF TKA Rehabilitation Protocol: https://eorif.com/node/995
--     • PMC8811524: Table 1 - TKA Phase I-II exercise progression
--       https://pmc.ncbi.nlm.nih.gov/articles/PMC8811524/table/tbl1/
--     • APTA Clinical Practice Guideline: Total Knee Arthroplasty (Draft)
--       https://www.apta.org/siteassets/pdfs/cpg/apta-cpg-total-knee-arthroplasty-manuscript-draft.pdf
--
--   髋关节置换术(THA)：
--     • NICE Guideline NG157: Joint replacement (primary) - hip, knee and shoulder (2020, reviewed 2024)
--       https://www.nice.org.uk/guidance/ng157
--     • AAOS OrthoInfo: Total Hip Replacement Exercise Guide
--       https://orthoinfo.aaos.org/en/recovery/total-hip-replacement-exercise-guide/
--     • PMC10612534: Table 1 - THA rehabilitation plan
--       https://pmc.ncbi.nlm.nih.gov/articles/PMC10612534/table/TAB1/
--     • PMC9440276: Table 1 - THA physiotherapy management week 1-4
--       https://pmc.ncbi.nlm.nih.gov/articles/PMC9440276/table/TAB1/
--
--   腰椎间盘手术(Lumbar Discectomy)：
--     • NHS Lothian: Post-operative Lumbar Discectomy Guidelines (May 2016)
--       https://apps.nhslothian.scot/files/sites/2/Post-op-lumbar-disectomy-guidelines-May-2016.pdf
--     • London Back Pain Clinic: Post-op Microdiscectomy Rehabilitation Protocol
--       https://www.londonbackpainclinic.com/wp-content/uploads/2019/02/Postop-Microdiscectomy-Rehabilitation.pdf
--     • Spine 2012;37(8):E485-E492: Postoperative management following lumbar discectomy
--       (Systematic Review, Evidence Level A1)

CREATE TABLE IF NOT EXISTS rehab_guidelines (
    id INT PRIMARY KEY AUTO_INCREMENT,
    surgery_type VARCHAR(100) NOT NULL COMMENT '手术类型标签',
    phase VARCHAR(20) NOT NULL COMMENT '康复阶段',
    category VARCHAR(30) NOT NULL COMMENT '指南类别',
    title VARCHAR(200) NOT NULL COMMENT '指南标题',
    content TEXT NOT NULL COMMENT '指南详细内容',
    evidence_level VARCHAR(50) DEFAULT '专家共识' COMMENT '证据等级',
    source VARCHAR(500) COMMENT '文献来源及URL',
    source_type VARCHAR(30) DEFAULT 'clinical_guideline' COMMENT '来源类型',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_surgery_phase (surgery_type, phase),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 膝关节置换术 (TKA) 循证康复指南
-- ============================================================================

INSERT INTO rehab_guidelines (surgery_type, phase, category, title, content, evidence_level, source, source_type) VALUES
('膝关节置换术', '急性期', 'exercise', '踝泵运动（Ankle Pumps）',
'术后即刻开始，清醒状态下每小时做1组。方法：平躺或半坐卧位，双脚同时用力勾脚尖（背屈）至最大角度→保持5秒→再用力踩脚尖（跖屈）至最大角度→保持5秒，此为1次。20次为1组。2025年meta分析（16项RCT，1704例患者）显示：踝泵运动使下肢骨科术后DVT发生率降低73%（OR=0.27, p<0.001），为Level I级证据。',
'Level I (Meta-analysis of RCTs)',
'https://eorif.com/node/995/printable/print | AAOS OrthoInfo TKA Exercise Guide | 2025 Meta-analysis: Ankle pump exercises vs DVT (OR=0.27)',
'clinical_guideline'),

('膝关节置换术', '急性期', 'exercise', '股四头肌等长收缩（Quad Sets）',
'术后第1天开始。平躺，患侧膝下垫一卷毛巾使膝关节微屈约15-20°。股四头肌用力收紧，感觉髌骨向头侧移动，膝关节后方下压毛巾卷。保持5-10秒后完全放松。10-15次/组×3-5组/天。目的：激活术后被关节源性抑制的股四头肌，防止伸膝迟滞。APTA TKA临床实践指南将此列为Phase I核心训练。第2周可进阶为毛巾卷垫于足跟下（长弧等长收缩），进一步增加伸膝末端的激活。',
'Level I (Clinical Practice Guideline)',
'https://www.apta.org/siteassets/pdfs/cpg/apta-cpg-total-knee-arthroplasty-manuscript-draft.pdf | AAOS OrthoInfo TKA Exercise Guide',
'clinical_guideline'),

('膝关节置换术', '急性期', 'exercise', '足跟滑动（Heel Slides）— 主动辅助屈膝',
'术后第1-2天开始。仰卧或坐位，患侧足跟沿床面缓慢向臀部方向滑动至最大可耐受屈膝角度（初期目标70°），保持5-10秒后缓慢滑回原位。10-15次/组×3组/天。关键注意事项：不过度施压（no overpressure），以轻微牵拉感为度，不使用外力推压膝关节。第一周末目标：屈膝≥70-90°，完全伸直0°。EORIF TKA Protocol将此列为Day 1-4的核心ROM训练。',
'Level I (Clinical Practice Guideline)',
'https://eorif.com/node/995/printable/print | PMC8811524 Table 1',
'clinical_guideline'),

('膝关节置换术', '急性期', 'exercise', '被动伸膝训练（Heel Prop / LLLD Stretch）',
'术后立即开始。平躺，足跟下方垫毛巾卷或枕头使小腿悬空，膝关节下方不垫任何东西，利用重力使膝关节自然下垂至完全伸直位。每次保持3-5分钟，每日多次。如伸膝仍>5°，可在膝关节上方（髌骨近端）加0.5-2kg沙袋辅助伸展。AAOS SMOAK CPG强调：获得完全伸膝（0°）是TKA术后最重要的功能目标之一，伸膝挛缩>10°将显著影响行走效率和步态对称性。',
'Level I (CPG)',
'https://www.aaos.org/smoak2cpg | AAOS OrthoInfo TKA Exercise Guide',
'clinical_guideline'),

('膝关节置换术', '急性期', 'medication', '术后多模式镇痛方案',
'根据AAOS 2022 SMOAK CPG（Strong Recommendation★★★★）：①推荐使用周围神经阻滞（PNB）——可减少术后疼痛及阿片类药物用量；②推荐关节周围局部浸润麻醉；③氨甲环酸(TXA)应常规使用（除非禁忌）。口服方案：NSAIDs作为基础（塞来昔布200mg QD或依托考昔60mg QD），必要时加用曲马多50mg q6-8h prn。目标：静息痛VAS≤3，活动痛VAS≤5。术前使用阿片类药物者术后功能恢复显著较差（AAOS 2022新增推荐）。',
'Strong Recommendation (★★★★)',
'https://www.aaos.org/smoak2cpg | AAOS CPG Summary, JAAOS 2023;31(24)',
'clinical_guideline'),

('膝关节置换术', '急性期', 'precaution', 'TKA急性期关键安全事项',
'①禁止膝关节屈曲>90°（可能损伤关节囊缝合和软组织）；②禁止旋转动作（假体-骨界面未愈合期）；③根据AAOS 2022 CPG：反对常规使用引流管（Moderate★★★）——不影响并发症或结局，且有利于早期活动；④如出现以下情况立即联系医师：伤口红肿热痛+发热>38.0°C（感染征象）、小腿明显肿胀+Homan征阳性（DVT征象）、突发胸痛+呼吸困难（肺栓塞征象）；⑤术后2周内保持伤口干燥，使用防水敷料洗澡。',
'Strong/Moderate (CPG)',
'https://www.aaos.org/smoak2cpg | AAOS CPG Summary, JAAOS 2023;31(24)',
'clinical_guideline'),

('膝关节置换术', '恢复期', 'exercise', '坐位主动伸膝（Short Arc Quads / Long Arc Quads）',
'术后2-6周。坐于椅上，患侧膝后垫毛巾卷使膝微屈，主动伸膝至完全伸直→保持5秒→缓慢放下。初期仅做0-30°短弧（SAQ），第4周可进阶为全弧（LAQ）从屈曲90°至完全伸直。15次/组×3组/天。当可无迟滞完成SAQ 15次×3组时（股四头肌力≥3+/5），可考虑减少助行器使用。AAOS OrthoInfo将此列为核心肌力训练。',
'Level I (CPG)',
'https://orthoinfo.aaos.org/en/recovery/total-knee-replacement-exercise-guide/ | PMC8811524 Table 1',
'clinical_guideline'),

('膝关节置换术', '恢复期', 'exercise', '靠墙半蹲（Wall Squats）— 闭链功能训练',
'术后3-4周开始（需确认股四头肌力≥3+/5级）。背靠墙壁，双足与肩同宽、距墙约30cm。缓慢下滑至半蹲位：初期屈膝≤30°，第4-5周增至≤45°，第6周可增至≤60°但不超过90°。保持30-60秒×3-5次/天。核心要点：膝盖始终不超过脚尖垂直线。此训练在多种TKA康复方案（EORIF, PMC8811524, APTA CPG）中被列为Phase II关键功能训练，可同时增强股四头肌、臀肌和腓肠肌，直接转化至上下楼梯功能。',
'Level I (Multiple CPGs)',
'https://eorif.com/node/995/printable/print | https://orthoinfo.aaos.org | APTA CPG TKA',
'clinical_guideline'),

('膝关节置换术', '恢复期', 'exercise', '步行训练进阶',
'术后2周：助行器辅助平地行走100米×2-3次/天；第3周：可减为单拐（健侧持拐）行走200米×3次/天；第4-5周：尝试室内脱拐行走（确保地面平坦干燥、无杂物）；第6周目标：独立连续行走500米，步态基本对称。AAOS OrthoInfo强调：从助行器→双拐→单拐→独立行走的过渡必须以步态质量为准——如出现跛行加重（Trendelenburg步态或避痛步态），应退回上一级辅助。步态要点：足跟先着地→全足滚动→足趾蹬离。',
'Level I (CPG)',
'https://orthoinfo.aaos.org/en/recovery/total-knee-replacement-exercise-guide/ | APTA CPG TKA',
'clinical_guideline'),

('膝关节置换术', '恢复期', 'review', '术后关键复查节点',
'①术后2周：拆线+伤口评估、首次正式ROM测量（伸膝/屈膝角度）、VAS评分、步态初评。②术后6周：门诊X线（评估假体对线、有无松动透亮线）、正式肌力评估（MMT）、独立行走能力评估。③术后12周（恢复期结束）：KOOS或WOMAC功能评分量表、关节活动度终测、确认可否回归工作和驾驶。APTA CPG推荐每次复查前由患者记录近一周的疼痛评分趋势、单次最大行走距离、可完成的新功能活动。',
'Level I (CPG)',
'https://www.apta.org/siteassets/pdfs/cpg/apta-cpg-total-knee-arthroplasty-manuscript-draft.pdf | AAOS SMOAK 2022',
'clinical_guideline'),

('膝关节置换术', '恢复期', 'diet', '恢复期营养支持',
'AAOS 2022 CPG新增推荐：优化围手术期血糖控制（Strong★★★★）——HbA1c<6.5%，空腹血糖<126mg/dL。营养支持：①每日蛋白质≥1.2g/kg体重，分4-5餐摄入（减少单次摄入代谢负担）；②钙1000mg/天+维生素D 800-1200IU/天；③有胃病史者NSAIDs需加用PPI（奥美拉唑20mg QD）。BMI≥40者手术部位感染风险显著增加，术前即应启动减重计划。',
'Strong Recommendation (★★★★)',
'https://www.aaos.org/smoak2cpg | AAOS CPG Summary, JAAOS 2023;31(24)',
'clinical_guideline'),

('膝关节置换术', '巩固期', 'exercise', '功率自行车训练',
'术后6周开始（需屈膝≥100°）。调整车座高度使踏板最低点时膝关节仍微屈（避免完全伸直锁死）。从无阻力开始，每次5-10分钟，逐步增加至20-30分钟/次，每周5-7天。初期只做部分圆周（前后方向踩踏）直到可完成完整圆周。APTA CPG将功率自行车列为Phase II→III过渡标誌性训练——完成20分钟连续蹬踏即可从恢复期进入巩固期。',
'Level I (CPG)',
'https://www.apta.org/siteassets/pdfs/cpg/apta-cpg-total-knee-arthroplasty-manuscript-draft.pdf',
'clinical_guideline'),

('膝关节置换术', '巩固期', 'exercise', '上下楼梯训练',
'术后8周开始（需屈膝≥105°+股四头肌力≥4/5级）。规则：上楼梯健侧腿先上→患侧腿跟上；下楼梯患侧腿先下→健侧腿跟下。扶扶手辅助。从2级台阶开始，每日增加2-3级，目标12周时不扶扶手完成2层楼梯。APTA CPG将此列为Phase III的功能里程碑。注意事项：禁止一步两级或跳跃式上下——这会对假体产生2-3倍体重的冲击力。',
'Level I (CPG)',
'https://www.apta.org/siteassets/pdfs/cpg/apta-cpg-total-knee-arthroplasty-manuscript-draft.pdf',
'clinical_guideline'),

('膝关节置换术', '巩固期', 'review', '长期随访与假体寿命维护',
'随访节点：术后3月→6月→1年→每年1次。AAOS 2022 CPG强调：①体重管理是影响假体寿命的最重要可改变因素——BMI<30可显著降低聚乙烯磨损率和无菌性松动风险；②避免高冲击活动（跑步、跳跃、对抗性运动）——产生3-5倍体重冲击力直接传递至假体-骨界面；③推荐低冲击运动：游泳、自行车、快走、高尔夫。人工关节预期使用寿命15-25年，体重控制和活动管理可延长5-10年。',
'Strong/Moderate (CPG)',
'https://www.aaos.org/smoak2cpg | AAOS CPG Summary, JAAOS 2023;31(24)',
'clinical_guideline');

-- ============================================================================
-- 髋关节置换术 (THA) 循证康复指南
-- ============================================================================

INSERT INTO rehab_guidelines (surgery_type, phase, category, title, content, evidence_level, source, source_type) VALUES
('髋关节置换术', '急性期', 'precaution', 'THA术后防脱位安全规则',
'NICE Guideline NG157(2020,2024年复审)及AAOS OrthoInfo明确THA术后防脱位要点。后方入路（最常见入路）术后12周内必须严格遵守：①屈髋不超过90°（使用加高马桶座和坐垫、不下蹲、不弯腰捡物）；②不内收过中线（双腿间夹枕或外展枕、禁止翘二郎腿）；③不内旋（脚尖始终朝前或稍朝外）。前方入路限制较少（不做过伸、不外旋>40°），通常6周。NICE NG157特别强调：出院前必须由理疗师明确告知患者个体化的关节位置注意事项。后方入路脱位风险约1-2%，其中57%的脱位患者会再次脱位，45.6%最终需翻修。',
'Guideline (NICE + AAOS)',
'https://www.nice.org.uk/guidance/ng157 | https://orthoinfo.aaos.org/en/recovery/total-hip-replacement-exercise-guide/',
'clinical_guideline'),

('髋关节置换术', '急性期', 'exercise', 'THA急性期床上活动（Phase I, Week 0-2）',
'术后即刻开始（PMC10612534 Table 1方案）。①踝泵：清醒时每1小时10-20次（DVT预防，2025年Meta-analysis：OR=0.27）；②股四头肌等长收缩：10次×1-2组，每日2次；③臀肌等长收缩：10次×1-2组（保持5秒）；④足跟滑动（床上屈髋滑行）：10次×1组，受90°限制；⑤仰卧髋外展（重力消除位）：量力而行。所有训练在平卧位完成，严格遵守90°规则。步行：术后当天或第1天即下床，助行器辅助，WBAT（Weight Bearing As Tolerated），行走5-10分钟×3-5次/天。',
'Guideline (NICE + PMC Table)',
'https://www.nice.org.uk/guidance/ng157 | https://pmc.ncbi.nlm.nih.gov/articles/PMC10612534/table/TAB1/',
'clinical_guideline'),

('髋关节置换术', '急性期', 'medication', 'THA术后VTE预防和镇痛',
'VTE预防方案同TKA（参照AAOS指南和《中国骨科大手术VTE预防指南》）：利伐沙班10mg QD或依诺肝素40mg SC QD，术后6-12h开始，持续14-35天。联合IPC直至可独立行走。AAOS 2022 CPG给出的Strong推荐同样适用于THA：周围神经阻滞(★★★★)、关节周围浸润(★★★★)、TXA常规使用(★★★★)。THA术中失血量通常>TKA（约300-500ml），术后需监测Hb，如<80g/L考虑输血。',
'Strong Recommendation (★★★★)',
'https://www.aaos.org/smoak2cpg | NICE NG157',
'clinical_guideline'),

('髋关节置换术', '恢复期', 'exercise', 'THA恢复期训练（Phase II, Week 2-6）',
'PMC10612534 Table 1 和 AAOS OrthoInfo方案。继续Phase I所有训练，新增：①桥式运动（双侧→单侧）：10次×2组（注意屈髋<90°）；②蚌式开合（Clamshells）：10次×2组；③侧卧髋外展：10次×2组；④坐位伸膝（SAQ/LAQ）：10次×2组；⑤坐→站训练：10次×2组（从加高座椅开始）；⑥站立位髋后伸/外展/内收：各10次×2组；⑦提踵：10次×2组；⑧功率自行车（无阻力+高座位）：5-10分钟。步态训练：第3周开始过渡至单拐→第4-6周独立行走。关键标准：疼痛<4/10、无Trendelenburg步态、足跟→足尖正常步态。⚠️6周前禁止抗阻训练（弹力带、负重、器械）。',
'Guideline (PMC + AAOS)',
'https://pmc.ncbi.nlm.nih.gov/articles/PMC10612534/table/TAB1/ | https://orthoinfo.aaos.org/en/recovery/total-hip-replacement-exercise-guide/',
'clinical_guideline'),

('髋关节置换术', '恢复期', 'exercise', '负重训练对THA恢复的影响',
'2023年系统综述（PMC9440276）：负重运动方案在6周内改善髋关节功能评分56.4%，而非负重方案仅改善39.8%（p<0.01）。床旁运动+步态训练组的Harris髋关节评分在5周时达78.1（对照组71.5），DVT发生率2.7%（对照组14.1%）。结论：早期安全负重训练是加速THA恢复的关键——前提是严格遵守手术入路特异性防脱位规则。',
'Level I (Systematic Review)',
'https://pmc.ncbi.nlm.nih.gov/articles/PMC9440276/table/TAB1/',
'clinical_guideline'),

('髋关节置换术', '巩固期', 'exercise', 'THA巩固期综合训练（Phase III, Week 6-12）',
'PMC10612534 + AAOS OrthoInfo方案。6周后安全解除大多数活动限制（经医生确认）。进阶训练：①单腿腿举（离心强调）；②台阶上下；③前弓步（控制ROM）；④靠墙静蹲至屈膝60°；⑤单腿站立进阶（稳定面→不稳定面如BOSU球）；⑥弹力带侧向行走/抗阻训练（6周后首次引入阻力）；⑦功率自行车增加阻力；⑧游泳（切口完全愈合后，约6周起）。重返运动时间表：游泳/高尔夫/自行车6周、徒步6周、瑜伽8周、跑步/滑雪8-12周。永久避免：高冲击运动（跑步/跳跃）、极限ROM（深度瑜伽）、重复提重物>50磅。',
'Guideline (PMC + AAOS)',
'https://pmc.ncbi.nlm.nih.gov/articles/PMC10612534/table/TAB1/ | https://orthoinfo.aaos.org/en/recovery/total-hip-replacement-exercise-guide/',
'clinical_guideline');

-- ============================================================================
-- 腰椎间盘手术 (Lumbar Discectomy) 循证康复指南
-- ============================================================================

INSERT INTO rehab_guidelines (surgery_type, phase, category, title, content, evidence_level, source, source_type) VALUES
('腰椎间盘手术', '急性期', 'precaution', '腰椎术后核心安全规则（BLT规则 + 早期活动）',
'来自NHS Lothian Guidelines (2016)和Spine系统综述(2012, Evidence Level A1)的核心建议。术后1-4周绝对遵守BLT规则：禁止Bending（弯腰前屈——使L3-S1椎间盘内压力急剧升高）；禁止Lifting（提重物>3-5kg/10-15磅）；禁止Twisting（扭转躯干——剪切力损伤纤维环修复）。积极证据：术后第1-2天即开始活动方案的患者，6-12周时VAS评分显著低于延迟活动者(Evidence Level B)。坐姿限制：每次≤15分钟、每日≤4次，使用腰靠。卧床翻身采用"滚木式"（Log Roll）——保持脊柱不扭转。',
'Level A1 (Systematic Review + NHS Guideline)',
'https://apps.nhslothian.scot/files/sites/2/Post-op-lumbar-disectomy-guidelines-May-2016.pdf | Spine 2012;37(8):E485-E492',
'clinical_guideline'),

('腰椎间盘手术', '急性期', 'exercise', '腹横肌激活 + 神经根滑动（Phase I, Week 0-4）',
'NHS Lothian方案（May 2016）。术后1-2天开始：①腹横肌激活（Abdominal Bracing）：平躺屈膝，感觉"将肚脐拉向脊柱"而腰部不动，保持正常呼吸10秒→放松，10-15次×3组/天——这是腰椎术后最安全的初始核心训练；②神经根滑动（Sciatic/Femoral Nerve Gliding）：术后2-3天开始，仰卧直腿抬高至神经牵拉感出现（不引发剧痛），保持5-10秒→缓慢放下，10次×3组/天——目的是促进神经根滑动、预防术后硬膜外纤维化（FBSS的重要原因之一）；③臀肌/股四头肌等长收缩；④踝泵（防DVT）。Walking：第1周平地行走5-7分钟×2-3次/天→第2-4周逐步增加至20-30分钟/天。',
'Level A1 (NHS Guideline + Systematic Review)',
'https://apps.nhslothian.scot/files/sites/2/Post-op-lumbar-disectomy-guidelines-May-2016.pdf | https://www.londonbackpainclinic.com/wp-content/uploads/2019/02/Postop-Microdiscectomy-Rehabilitation.pdf',
'clinical_guideline'),

('腰椎间盘手术', '恢复期', 'exercise', '核心稳定训练（Phase II, Week 4-12）',
'NHS Lothian (Evidence Level A1)：从术后约第4周开始主动运动方案的患者，其疼痛和功能改善速度快于不接受治疗者，且不增加再手术率(Level A1)。①鸟狗式（Bird Dog）：四足跪姿，交替伸直对侧手臂和腿，每侧8-10次×3组/天——全程保持脊柱不动（背上可放书监测）；②改良平板支撑：膝着地→脚尖着地进阶，从10秒×3组起逐步延长至60秒；③侧桥：每侧10-30秒×3组；④"死虫式"（Dead Bug）：仰卧，交替伸展对侧手臂和腿——腹横肌和多裂肌的协调训练。⑤功率自行车（第4周起，无阻力）；⑥游泳（第6周起，切口完全愈合）。核心原则：进展以不引发腰痛为准——出现疼痛退回上一级难度。',
'Level A1 (Systematic Review + NHS)',
'https://apps.nhslothian.scot/files/sites/2/Post-op-lumbar-disectomy-guidelines-May-2016.pdf | Spine 2012;37(8):E485-E492',
'clinical_guideline'),

('腰椎间盘手术', '恢复期', 'exercise', '恢复期活动进阶时间表',
'NHS Lothian 2016 + London Back Pain Clinic Protocol：更高强度运动方案带来更快的疼痛/功能改善和更早的复工(Level A1)。驾驶：2-4周（需确认可完成紧急刹车动作、未使用镇静镇痛药）。重返活动时间节点：游泳6周、高尔夫6周、徒步6周、瑜伽8周、户外自行车6周、跑步/慢跑8-12周、滑雪8周。复工：久坐办公4-6周、体力劳动8-12周（需通过Functional Capacity Evaluation）。Spine 2012系统综述指出：居家训练方案如有良好依从性，与有监督理疗方案效果相当(Evidence Level A1)。',
'Level A1 (Systematic Review + NHS)',
'https://apps.nhslothian.scot/files/sites/2/Post-op-lumbar-disectomy-guidelines-May-2016.pdf | Spine 2012;37(8):E485-E492',
'clinical_guideline'),

('腰椎间盘手术', '巩固期', 'exercise', '返回运动/工作的高级训练（Phase III, 3-6月）',
'NHS Lothian Phase III标准：进入条件——无疼痛加重、无活动度或功能退步、在各种体位下均能保持脊柱中立位、良好的动态腰椎稳定性。训练内容：①多平面核心稳定（Swiss球、BOSU球、平衡板）；②渐进抗阻训练（不再仅限于等长收缩）；③跑步方案（8-12周启动、步态教育）；④敏捷性训练；⑤运动/职业特定模拟训练。提重物限制：术后6周内<10-15磅（5-7kg）→术后12周内<25-30磅（11-14kg）→术后6个月回归全量负重。FCE（功能性能力评估）用于确定复工安全。',
'Level A1 (NHS Guideline + Systematic Review)',
'https://apps.nhslothian.scot/files/sites/2/Post-op-lumbar-disectomy-guidelines-May-2016.pdf',
'clinical_guideline');

-- ============================================================================
-- 通用康复原则（适用于所有手术类型）
-- ============================================================================

INSERT INTO rehab_guidelines (surgery_type, phase, category, title, content, evidence_level, source, source_type) VALUES
('通用', '通用', 'general', '加速康复外科(ERAS)核心原则',
'来自NICE NG157(2020)、AAOS SMOAK CPG(2022)和《中国骨科大手术加速康复围手术期管理专家共识》的共同原则：①术前教育：告知患者康复过程、预期疼痛水平、功能恢复时间线（减少恐惧-回避行为，提高治疗依从性）；②多模式镇痛：NSAIDs基础+区域阻滞+必要时弱阿片（目标VAS≤3静息/VAS≤5活动）；③早期活动：术后当天或第1天即下床，无特殊情况不卧床（Strong Recommendation）；④早期经口进食：麻醉苏醒后评估吞咽功能即开始流质；⑤围手术期血糖管理：空腹<126mg/dL，HbA1c<6.5%（AAOS 2022 Strong★★★★）；⑥VTE预防：药物+物理联合预防。',
'Guideline (Multiple CPGs)',
'https://www.nice.org.uk/guidance/ng157 | https://www.aaos.org/smoak2cpg | 中国骨科大手术加速康复专家共识',
'clinical_guideline'),

('通用', '通用', 'general', '康复训练通用安全原则',
'综合NICE NG157、AAOS OrthoInfo、APTA CPG的安全原则：①疼痛是信号——运动后肌肉酸痛正常；尖锐/加剧/新发关节痛提示需要减量或临床评估；②进展以功能达标为准——不可仅按日历推进（例：能无迟滞完成SAQ 15次×3组方可进入LAQ训练）；③康复训练不应每次需要止痛药——如果每次训练后需服阿片类才能忍受，说明强度过大；④冰敷+抬高+加压是任何训练后的标配（每次训练后冰敷20分钟可减少疼痛和肿胀的炎症反应）；⑤如果连续1周功能无改善（<5°ROM增加或无明显肌力进步），应联系治疗师/医师重新评估。',
'Guideline (Multiple CPGs)',
'https://www.nice.org.uk/guidance/ng157 | https://orthoinfo.aaos.org | APTA CPG TKA Draft',
'clinical_guideline');
