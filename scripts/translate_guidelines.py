# -*- coding: utf-8 -*-
"""
康复运动内容英→中翻译脚本
使用专业词典 + 句式模板替换，零API调用
"""

import sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db.session import db_instance

# ============================================================
# 运动名称词典
# ============================================================
EXERCISE_NAMES = {
    "Heel Cord Stretch": "跟腱拉伸",
    "Standing Quadriceps Stretch": "站立股四头肌拉伸",
    "Supine Hamstring Stretch": "仰卧腘绳肌拉伸",
    "Half Squats": "半蹲训练",
    "Hamstring Curls": "腘绳肌弯举",
    "Calf Raises": "提踵训练",
    "Leg Extensions": "坐位伸膝",
    "Straight Leg Raises": "直腿抬高",
    "Straight-Leg Raises": "直腿抬高",
    "Straight-Leg Raises (Prone)": "俯卧直腿抬高",
    "Hip Abduction": "髋外展训练",
    "Hip Adduction": "髋内收训练",
    "Leg Presses": "腿部推举",
    "Getting Started": "开始之前",
    "Pendulum, Circular (Codman's Exercises)": "钟摆运动（Codman训练）",
    "Shoulder Forward Elevation (Assisted)": "肩关节前屈（辅助）",
    "Supported Shoulder Rotation (Assisted)": "支撑肩关节旋转（辅助）",
    "Shoulder Internal Rotation (Assisted)": "肩关节内旋（辅助）",
    "Walk Up Exercise (Active)": "爬墙运动（主动）",
    "Shoulder Forward Elevation (Active)": "肩关节前屈（主动）",
    "Shoulder Abduction (Active)": "肩关节外展（主动）",
    "Shoulder Extension (Isometric)": "肩关节后伸（等长收缩）",
    "Shoulder Internal Rotation (Isometric)": "肩关节内旋（等长收缩）",
    "Shoulder External Rotation (Isometric)": "肩关节外旋（等长收缩）",
    "Shoulder Internal Rotation (with Band)": "肩关节内旋（弹力带）",
    "Shoulder External Rotation (with Band)": "肩关节外旋（弹力带）",
    "Shoulder Adduction (Isometric)": "肩关节内收（等长收缩）",
    "Scapular Retraction (Isometric)": "肩胛骨后缩（等长收缩）",
    "Biceps Curl": "肱二头肌弯举",
    "Triceps Extension": "肱三头肌伸展",
    "Early Post-Operative Exercises": "术后早期训练",
    "Early Activity": "早期活动",
    "Advanced Exercises and Activities": "进阶训练与活动",
    "Head Rolls": "头部旋转",
    "Kneeling Back Extension": "跪姿背伸",
    "Sitting Rotation Stretch": "坐姿旋转拉伸",
    "Modified Seat Side Straddle": "改良坐姿侧分腿",
    "Knee to Chest": "抱膝触胸",
    "Bird Dog": "鸟狗式",
    "Plank": "平板支撑",
    "Modified Side Plank": "改良侧桥",
    "Hip Bridge": "臀桥",
    "Abdominal Bracing": "腹肌收紧",
    "Abdominal Crunch": "卷腹",
    "Golf Ball Roll": "高尔夫球滚动",
    "Towel Stretch": "毛巾拉伸",
    "Ankle Range of Motion": "踝关节活动度训练",
    "Marble Pickup": "弹珠捡拾",
    "Towel Curls": "毛巾卷曲",
    "Single Leg Balance": "单腿站立平衡",
    "Crossover Arm Stretch": "交叉手臂拉伸",
    "Passive Internal Rotation": "被动内旋",
    "Passive External Rotation": "被动外旋",
    "Sleeper Stretch": "侧卧拉伸",
    "Standing Row": "站立划船",
    "Elbow Flexion": "肘屈曲",
    "Elbow Extension": "肘伸展",
    "Trapezius Strengthening": "斜方肌强化",
    "Scapula Setting": "肩胛骨定位",
    "Bent-Over Horizontal Abduction": "俯身水平外展",
}

# ============================================================
# 肌肉/身体部位词典
# ============================================================
MUSCLE_MAP = {
    "Gastrocnemius-soleus complex": "腓肠肌-比目鱼肌复合体（小腿后侧）",
    "Quadriceps": "股四头肌（大腿前侧）",
    "Hamstrings": "腘绳肌（大腿后侧）",
    "Gluteus medius and gluteus maximus": "臀中肌和臀大肌",
    "Gluteals": "臀肌",
    "Gluteus": "臀肌",
    "Abductors": "外展肌群（大腿外侧）",
    "Adductors": "内收肌群（大腿内侧）",
    "Gastrocnemius": "腓肠肌",
    "Soleus": "比目鱼肌",
    "Tibialis anterior": "胫骨前肌",
    "Posterior tibialis": "胫骨后肌",
    "Peroneals": "腓骨肌群",
    "Plantar fascia": "足底筋膜",
    "Deltoids": "三角肌",
    "Rotator cuff": "肩袖肌群",
    "Trapezius": "斜方肌",
    "Rhomboids": "菱形肌",
    "Biceps": "肱二头肌",
    "Triceps": "肱三头肌",
    "Erector spinae": "竖脊肌",
    "Latissimus dorsi": "背阔肌",
    "Abdominals": "腹肌",
    "Tensor fascia latae": "阔筋膜张肌",
    "Piriformis": "梨状肌",
    "Deltoids": "三角肌",
    "supraspinatus": "冈上肌",
    "infraspinatus": "冈下肌",
    "subscapularis": "肩胛下肌",
    "teres minor": "小圆肌",
    "Posterior deltoid": "三角肌后束",
    "Supraspinatus": "冈上肌",
    "Anterior deltoid": "三角肌前束",
    "calf": "小腿",
    "thigh": "大腿",
    "buttock": "臀部",
    "buttocks": "臀部",
    "shoulder": "肩部",
    "knee": "膝关节",
    "hip": "髋关节",
    "back": "背部",
    "neck": "颈部",
    "foot": "足部",
    "ankle": "踝关节",
    "elbow": "肘部",
    "wrist": "腕部",
    "heel": "足跟",
}

# ============================================================
# 动作/句式词典（按优先级排序，长的先匹配）
# ============================================================
PHRASE_MAP = [
    # 标准标题
    ("Main muscles worked:", "目标肌肉："),
    ("You should feel this stretch in your", "拉伸应感受到的部位："),
    ("You should feel this exercise in your", "训练应感受到的部位："),
    ("You should feel this exercise at the front of your thigh", "您应感受到大腿前侧的发力"),
    ("You should feel this exercise at the back of your thigh", "您应感受到大腿后侧的发力"),
    ("You should feel this exercise in your calf", "您应感受到小腿的发力"),
    ("You should feel this exercise at your outer thigh and buttock", "您应感受到大腿外侧和臀部的发力"),
    ("You should feel this exercise at your inner thigh", "您应感受到大腿内侧的发力"),
    ("You should feel this exercise at the front and back of your thighs, and your buttocks", "您应感受到大腿前后侧及臀部的发力"),
    ("You should feel this stretch at the back of your thigh and behind your knee", "您应感受到大腿后侧和膝后的拉伸感"),
    ("and into your heel", "并延伸至足跟"),
    ("You should feel this exercise at the front of your hip, and the front and back of your thigh", "您应感受到髋部前侧及大腿前后侧的发力"),
    ("Equipment needed:", "所需器材："),
    ("Equipment needed", "所需器材"),
    ("Step-by-step directions", "分步指导"),
    ("Repetitions", "组数/次数"),
    ("Days Per Week:", "每周天数："),
    ("Days Per Week: 5 to 6", "每周5-6天"),
    ("Days Per Week: 3 to 4", "每周3-4天"),
    ("Days Per Week: 6 to 7", "每周6-7天"),
    ("Days Per Week: 4 to 5", "每周4-5天"),
    ("Days Per Week: Daily", "每天"),
    ("You should feel this stretch at the back of your shoulder", "您应感受到肩部后侧的拉伸"),
    ("You should feel this stretch in the back of your shoulder", "您应感受到肩部后侧的拉伸"),
    ("You should feel this stretch at the front of your shoulder", "您应感受到肩部前侧的拉伸"),
    ("Light stick, such as a yardstick (wooden ruler)", "轻质棍棒，如码尺（木尺）"),
    ("Lean forward and place one hand on a", "向前倾斜，将一只手放在"),
    ("Relax your shoulders", "放松肩膀"),
    ("Tuck your chin", "收下巴"),
    ("Roll your head", "缓慢转动头部"),
    ("Bring your chin to your chest", "将下巴贴近胸口"),
    ("Bring your ear to your shoulder", "将耳朵贴近肩膀"),
    ("Tilt your head back", "头部后仰"),
    ("Maintain a slight bend in your elbows", "保持肘关节微屈"),
    ("With your arms straight", "手臂伸直"),
    ("slide your hands forward", "双手向前滑动"),
    ("Return to starting position", "回到起始位置"),
    ("Return to the starting position", "回到起始位置"),
    ("Squeeze your shoulder blades together", "用力将肩胛骨向中间夹紧"),
    ("Lower your hips to the floor", "将臀部降低至地面"),
    ("Slowly lift one leg", "缓慢抬起一条腿"),
    ("Lower your hips down", "降低臀部"),
    ("Squeeze your gluteus", "收紧臀肌"),
    ("Place the center of the elastic band at the arch of your foot", "将弹力带中部置于足弓"),
    ("hold the ends in each hand", "双手各持弹力带一端"),
    ("Push your foot out straight", "将脚向前蹬直"),
    ("flex your toes toward your body", "脚趾朝向身体背屈"),
    ("Relax your toes", "放松脚趾"),
    ("Pull your toes toward your body", "将脚趾拉向身体"),
    ("Marble pickups", "弹珠捡拾"),
    ("Place 20 marbles on the floor", "在地板上放20颗弹珠"),
    ("Pick up one marble at a time with your toes", "用脚趾一次捡起一颗弹珠"),
    ("and put it in a bowl", "放入碗中"),
    ("Stand on one leg", "单腿站立"),
    ("maintaining your balance", "保持平衡"),
    ("Tilt your upper body forward", "上身微微前倾"),
    ("Tilt your body to the side", "身体向一侧倾斜"),
    ("Tilt your head to the side", "头向一侧倾斜"),
    ("your arms hanging down", "手臂自然下垂"),
    ("Lean forward and support yourself", "向前倾斜并支撑身体"),
    ("Repeat on the other side", "换另一侧重复"),
    ("Repeat with", "用"),
    ("your arm hanging down", "手臂自然下垂"),
    ("Gently pull", "缓慢拉动"),
    ("(wooden ruler)", "（木尺）"),
    ("(assisted)", "（辅助）"),
    ("against a wall", "靠墙"),
    ("Grasp the ends of the towel", "抓住毛巾两端"),
    ("loop a towel around", "将毛巾环绕"),
    ("Pull your leg toward you", "将腿向身体方向拉动"),
    ("point your toes toward the ceiling", "脚趾指向天花板"),
    ("Push your knee down", "将膝盖向下压"),
    ("Straighten your knee", "伸直膝关节"),
    ("Tighten the muscle on top of your thigh", "收紧大腿前侧肌肉"),
    ("Rest your arms at your sides", "手臂放松置于身体两侧"),
    ("Gently pull your ankle", "缓慢拉动脚踝"),
    ("Bring your heel toward your buttock", "将脚跟拉向臀部"),
    ("Place a rolled towel under your ankle", "将卷起的毛巾垫于踝下"),
    ("Let your knee relax into extension", "让膝关节自然放松伸展"),
    ("Place a rolled towel under your knee", "将卷起的毛巾垫于膝下"),
    ("Days Per Week", "每周训练天数"),
    ("None", "无需器材"),
    ("Chair for support", "椅子辅助"),
    # 动作指令
    ("Stand facing a wall with", "面朝墙壁站立，"),
    ("Stand with your feet shoulder distance apart", "双脚与肩同宽站立"),
    ("Stand with your weight evenly distributed over both feet", "双脚均匀承重站立"),
    ("Hold on to the back of a chair or a wall for balance", "扶住椅背或墙壁以保持平衡"),
    ("Hold onto the back of a chair or a wall for balance", "扶住椅背或墙壁以保持平衡"),
    ("Lie on the floor with both legs bent", "仰卧，双膝弯曲"),
    ("Lie on the floor on your stomach with your legs straight", "俯卧，双腿伸直"),
    ("Lie on the floor with your elbows directly under your shoulders", "仰卧，双肘置于肩部正下方"),
    ("Lie on your side with", "侧卧，"),
    ("Lie down on the floor on the side of", "侧卧于地板上，"),
    ("Lie on your back with", "仰卧，"),
    ("Sit up straight on a chair or bench", "在椅子或长凳上坐直"),
    ("Slowly lower", "缓慢放下"),
    ("slowly raise", "缓慢抬起"),
    ("slowly lower", "缓慢放下"),
    ("Hold this position for", "保持此姿势"),
    ("Hold this stretch for", "保持此拉伸"),
    ("and then relax", "然后放松"),
    ("Repeat", "重复"),
    ("Repeat with the opposite leg", "换另一侧腿重复"),
    ("Bend your knee and", "屈膝，"),
    ("Straighten your leg and", "伸直腿部，"),
    ("Keep both heels flat on the floor", "双足跟平贴地面"),
    ("Press your hips forward", "将髋部向前推"),
    ("Do not arch your back", "不要弓背"),
    ("Do not arch or twist your back", "不要弓背或扭转背部"),
    ("Do not put your hands at your knee joint and pull", "不要将手放在膝关节处用力拉"),
    ("Keep your chest lifted", "保持胸部上提"),
    ("Plant your weight in your heels", "将重心放在足跟上"),
    ("Push through your heels", "通过足跟发力推起"),
    ("Do not bend forward at your waist", "不要从腰部前倾"),
    ("Flex your foot and keep your knees close together", "脚背屈曲，双膝并拢"),
    ("Lift your unaffected foot off of the floor", "将健侧脚抬离地面"),
    ("Raise the heel of your affected foot as high as you can", "将患侧脚跟尽可能抬高"),
    ("Keep your weight centered on the ball of your working foot", "将重心保持在发力脚的前脚掌"),
    ("Tighten your thigh muscles and", "收紧大腿肌肉，"),
    ("Squeeze your thigh muscles and", "用力收缩大腿肌肉，"),
    ("Do not swing your leg or use forceful momentum", "不要甩腿或用惯性发力"),
    ("Do not tense up in your neck and shoulders", "不要紧绷颈部和肩部"),
    ("Keep your affected leg straight", "保持患侧腿伸直"),
    ("Tighten the thigh muscle of your affected leg", "收紧患侧大腿肌肉"),
    ("slowly raise it", "缓慢抬起"),
    ("Hold this position for 5 seconds and then relax and bring your leg to the floor", "保持5秒后放松，将腿放回地面"),
    ("Rest your head on your arms", "将头枕在手臂上"),
    ("Tighten your gluteus and hamstring muscles", "收紧臀肌和腘绳肌"),
    ("Keep your pelvic bones on the floor", "保持骨盆贴地"),
    ("Do not rotate your leg in an effort to raise it higher", "不要为了抬更高而旋转腿部"),
    ("Cross the uninjured leg in front of the injured leg", "将健侧腿交叉置于患侧腿前方"),
    ("Place your hand on the floor in front of your stomach for support", "将手置于腹部前方的地板上以支撑"),
    ("Keep your abdominals tight throughout the exercise", "整个训练过程中保持腹部收紧"),
    # 通用
    ("seconds", "秒"),
    ("minutes", "分钟"),
    ("Repeat.", "重复。"),
    ("sets of", "组，每组"),
    ("times per session", "次/组"),
    ("sessions a day", "组/天"),
    ("Do 3 sessions a day", "每天做3组"),
    ("per session", "/组"),
    ("Bend forward", "向前弯腰"),
    ("placing your", "将您的"),
    ("on a table for support", "放在桌上以支撑"),
    ("Rock your body in a circular pattern", "以画圆方式晃动身体"),
    ("clockwise", "顺时针"),
    ("counterclockwise", "逆时针"),
    ("Clasp your hands together and lift your arms above your head", "双手交握，举过头顶"),
    ("Keep your elbows as straight as possible", "保持肘关节尽量伸直"),
    ("Maintain the elevation for", "保持上举姿势"),
    ("Slowly lower your arms", "缓慢放下手臂"),
    ("Keep your elbow in place", "保持肘部固定"),
    ("your shoulder blades down and together", "肩胛骨下沉并内收"),
    ("Slide your forearm back and forth", "前后来回滑动手臂"),
    ("using a stick or cane to assist", "可使用棍棒辅助"),
    ("Use your other hand or a towel to help bring", "用另一只手或毛巾辅助将"),
    ("behind your back", "背到身后"),
    ("across to the opposite side", "跨到对侧"),
    ("With your elbow straight, use your fingers to 'crawl' up a wall", "肘伸直，用手指沿墙壁向上'爬行'"),
    ("as far as possible", "尽可能高"),
    ("Hold for", "保持"),
    ("Raise your arm upward to point to the ceiling", "向上抬臂指向天花板"),
    ("keeping your elbows straight and leading with your thumb", "肘伸直，拇指引领"),
    ("Raise your arm out to the side", "将手臂向侧方抬起"),
    ("with your elbow straight and your palm downward", "肘伸直，掌心朝下"),
    ("Do not shrug your shoulder or tilt your trunk", "不要耸肩或倾斜躯干"),
    ("Stand with your back against the wall", "背靠墙壁站立"),
    ("your arms straight at your sides", "手臂伸直置于身体两侧"),
    ("push your arms back into the wall", "将手臂向后推压墙壁"),
    ("and then relax", "然后放松"),
    ("begin with", "起始重量"),
    ("gradually progress to", "逐步进阶至"),
    ("As the exercise becomes easier to perform, gradually increase the resistance by adding an ankle weight", "随着训练逐渐变得轻松，可逐步增加踝部负重来增加阻力"),
    ("As the exercise becomes easier to perform, gradually increase the resistance by holding hand weights", "随着训练逐渐变得轻松，可逐步增加手持负重"),
    ("If you have access to a fitness center, this exercise can also be performed on a weight machine", "如有健身条件，此训练也可在器械上完成"),
    ("A fitness assistant at your gym can instruct you on how to use the machines safely", "健身房工作人员可指导您安全使用器械"),
    ("This exercise is best performed using an elastic stretch band of comfortable resistance", "此训练最宜使用弹性适中的弹力带"),
    ("Do not use ankle weights with this exercise", "此训练请勿使用踝部负重"),
    ("To ensure that this program is safe and effective for you, it should be performed under your doctor's supervision", "为确保此方案对您安全有效，请在医生指导下进行训练"),
    ("Talk to your doctor or physical therapist about which exercises will best help you meet your rehabilitation goals", "请与您的医生或理疗师讨论哪些训练最能帮助您达成康复目标"),
    ("After an injury or surgery, an exercise conditioning program will help you return to daily activities", "受伤或手术后，系统性训练方案有助于您恢复日常活动能力"),
    ("Following a well-structured conditioning program will also help you return to sports and other recreational activities", "遵循结构化的训练方案也有助于您重返运动和其他休闲活动"),
    ("Strength", "力量训练"),
    ("Flexibility", "柔韧性训练"),
    ("Target Muscles", "目标肌群"),
    ("Length of program", "训练周期"),
    ("This should be continued for 4 to 6 weeks", "本方案应持续进行4至6周"),
    ("unless otherwise specified by your doctor or physical therapist", "除非医生或理疗师另有建议"),
    ("After your recovery, these exercises can be continued as a maintenance program", "康复后，这些训练可作为维持方案继续进行"),
    ("Performing the exercises two to three days a week will maintain strength and range of motion", "每周进行2-3天训练即可维持力量和关节活动度"),
    ("Warmup", "热身"),
    ("Before doing the following exercises, warm up with 5 to 10 minutes of low impact activity, like walking or riding a stationary bicycle", "训练前，进行5-10分钟低强度活动热身，如步行或骑行固定自行车"),
    ("After the warm-up, do the stretching exercises before moving on to the strengthening exercises", "热身后，先做拉伸训练再进行力量训练"),
    ("When you have completed the strengthening exercises, repeat the stretching exercises to end the program", "完成力量训练后，再次进行拉伸训练以结束本次训练"),
    ("Do not ignore pain", "不要忽视疼痛"),
    ("You should not feel pain during an exercise", "训练过程中不应感到疼痛"),
    ("Talk to your doctor or physical therapist if you have any pain while exercising", "如训练中出现任何疼痛，请告知医生或理疗师"),
    ("Ask questions", "如有疑问"),
    ("If you are not sure how to do an exercise, or how often to do it, contact your doctor or physical therapist", "如不确定如何训练或训练频率，请联系医生或理疗师"),
    ("Stretch", "拉伸"),
    ("Warm-up", "热身"),
    ("Strengthening", "力量训练"),
    ("Main muscles worked", "目标肌肉"),
    ("as shown", "如图所示"),
    ("Repeat 10 times per session", "每组重复10次"),
    ("Repeat 5 to 10 times per session", "每组重复5-10次"),
    ("Repeat 3 times per session", "每组重复3次"),
    ("Repeat 10 to 20 times per session", "每组重复10-20次"),
    ("Repeat 10 times", "重复10次"),
    ("Repeat 3 times", "重复3次"),
    ("Repeat 5 to 10 times", "重复5-10次"),
    ("Repeat 10 to 20 times", "重复10-20次"),
    ("your uninvolved hand", "健侧手"),
    ("your involved hand", "患侧手"),
    ("affected leg", "患侧腿"),
    ("affected foot", "患侧脚"),
    ("unaffected leg", "健侧腿"),
    ("unaffected foot", "健侧脚"),
    ("injured leg", "患侧腿"),
    ("uninjured leg", "健侧腿"),
    ("affected knee", "患侧膝"),
    ("working foot", "发力脚"),
    ("top leg", "上方腿"),
    ("bottom leg", "下方腿"),
    ("Weight Bearing as Tolerated", "可耐受负重"),
    ("WBAT", "可耐受负重行走"),
]


def translate_text(text: str) -> str:
    """应用词典翻译单段文本"""
    if not text:
        return text

    result = text

    # 翻译运动名称（只在行首或特定位置）
    for en, cn in sorted(EXERCISE_NAMES.items(), key=lambda x: -len(x[0])):
        # 匹配以数字序号开头的情况: "1. Heel Cord Stretch"
        result = re.sub(rf'(\d+\.\s*){re.escape(en)}', rf'\1{cn}', result)
        # 匹配在行首出现
        result = re.sub(rf'^{re.escape(en)}$', cn, result, flags=re.MULTILINE)

    # 翻译肌肉名称
    for en, cn in sorted(MUSCLE_MAP.items(), key=lambda x: -len(x[0])):
        result = result.replace(en, cn)

    # 翻译词组（按长度优先，避免短词吃长词）
    for en, cn in PHRASE_MAP:
        result = result.replace(en, cn)

    return result


def translate_all():
    if not db_instance._ensure_connection():
        print("DB connect failed")
        return

    cursor = db_instance.connection.cursor(dictionary=True)
    cursor.execute("SELECT id, content FROM guideline_chunks WHERE content != '' AND content NOT LIKE '%目标肌肉%'")
    rows = cursor.fetchall()
    cursor.close()

    translated = 0
    for row in rows:
        cn = translate_text(row["content"])
        if cn != row["content"]:
            cursor = db_instance.connection.cursor()
            cursor.execute("UPDATE guideline_chunks SET content = %s WHERE id = %s", (cn, row["id"]))
            db_instance.connection.commit()
            cursor.close()
            translated += 1

    print(f"Translated {translated}/{len(rows)} chunks")


if __name__ == "__main__":
    translate_all()
