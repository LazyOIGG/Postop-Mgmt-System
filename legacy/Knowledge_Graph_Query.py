def add_shuxing_prompt(entity, shuxing, client):
    """
    查询疾病属性的辅助函数（疾病简介、病因、预防措施等）
    """
    add_prompt = ""
    try:
        sql_q = "match (a:疾病{名称:'%s'}) return a.%s" % (entity, shuxing)
        res = client.run(sql_q).data()[0].values()
        add_prompt += f"<提示>"
        add_prompt += f"用户对{entity}可能有查询{shuxing}需求，知识库内容如下："
        if len(res) > 0:
            join_res = "".join(res)
            add_prompt += join_res
        else:
            add_prompt += "图谱中无信息，查找失败。"
        add_prompt += f"</提示>"
    except:
        pass
    return add_prompt

def add_lianxi_prompt(entity, lianxi, target, client):
    """
    查询疾病关系的辅助函数（症状、药品、食物等）
    """
    add_prompt = ""
    
    try:
        sql_q = "match (a:疾病{名称:'%s'})-[r:%s]->(b:%s) return b.名称" % (entity, lianxi, target)
        res = client.run(sql_q).data()
        res = [list(data.values())[0] for data in res]
        add_prompt += f"<提示>"
        add_prompt += f"用户对{entity}可能有查询{lianxi}需求，知识库内容如下："
        if len(res) > 0:
            join_res = "、".join(res)
            add_prompt += join_res
        else:
            add_prompt += "图谱中无信息，查找失败。"
        add_prompt += f"</提示>"
    except:
        pass
    return add_prompt

def generate_prompt(response, query, client, bert_model, bert_tokenizer, rule, tfidf_r, device, idx2tag):
    """
    根据意图识别结果和实体，查询知识图谱并生成提示
    """
    # 实体识别
    entities = zwk.get_ner_result(bert_model, bert_tokenizer, query, rule, tfidf_r, device, idx2tag)
    
    yitu = []  # 实际使用的意图列表
    prompt = "<指令>你是一个医疗问答机器人，你需要根据给定的提示回答用户的问题。请注意，你的全部回答必须完全基于给定的提示，不可自由发挥。如果根据提示无法给出答案，立刻回答“根据已知信息无法回答该问题”。</指令>"
    prompt += "<指令>请你仅针对医疗类问题提供简洁和专业的回答。如果问题不是医疗相关的，你一定要回答“我只能回答医疗相关的问题。”，以明确告知你的回答限制。</指令>"
    # 特殊处理：只有症状没有疾病的情况
    if '疾病症状' in entities and '疾病' not in entities:
        sql_q = "match (a:疾病)-[r:疾病的症状]->(b:疾病症状 {名称:'%s'}) return a.名称" % (entities['疾病症状'])
        res = list(client.run(sql_q).data()[0].values())
        if len(res) > 0:
            entities['疾病'] = random.choice(res)
            all_en = "、".join(res)
            prompt += f"<提示>用户有{entities['疾病症状']}的情况，知识库推测其可能是得了{all_en}。请注意这只是一个推测，你需要明确告知用户这一点。</提示>"
    
    pre_len = len(prompt)  # 记录当前提示长度
    
    # 根据意图识别结果查询知识图谱
    if "简介" in response:
        if '疾病' in entities:
            prompt += add_shuxing_prompt(entities['疾病'], '疾病简介', client)
            yitu.append('查询疾病简介')
    
    if "病因" in response:
        if '疾病' in entities:
            prompt += add_shuxing_prompt(entities['疾病'], '疾病病因', client)
            yitu.append('查询疾病病因')
    
    if "预防" in response:
        if '疾病' in entities:
            prompt += add_shuxing_prompt(entities['疾病'], '预防措施', client)
            yitu.append('查询预防措施')
    
    if "治疗周期" in response:
        if '疾病' in entities:
            prompt += add_shuxing_prompt(entities['疾病'], '治疗周期', client)
            yitu.append('查询治疗周期')
    
    if "治愈概率" in response:
        if '疾病' in entities:
            prompt += add_shuxing_prompt(entities['疾病'], '治愈概率', client)
            yitu.append('查询治愈概率')
    
    if "易感人群" in response:
        if '疾病' in entities:
            prompt += add_shuxing_prompt(entities['疾病'], '疾病易感人群', client)
            yitu.append('查询疾病易感人群')
    
    if "药品" in response:
        if '疾病' in entities:
            prompt += add_lianxi_prompt(entities['疾病'], '疾病使用药品', '药品', client)
            yitu.append('查询疾病使用药品')
    
    if "宜吃食物" in response:
        if '疾病' in entities:
            prompt += add_lianxi_prompt(entities['疾病'], '疾病宜吃食物', '食物', client)
            yitu.append('查询疾病宜吃食物')
    
    if "忌吃食物" in response:
        if '疾病' in entities:
            prompt += add_lianxi_prompt(entities['疾病'], '疾病忌吃食物', '食物', client)
            yitu.append('查询疾病忌吃食物')
    
    if "检查项目" in response:
        if '疾病' in entities:
            prompt += add_lianxi_prompt(entities['疾病'], '疾病所需检查', '检查项目', client)
            yitu.append('查询疾病所需检查')
    
    if "查询疾病所属科目" in response:
        if '疾病' in entities:
            prompt += add_lianxi_prompt(entities['疾病'], '疾病所属科目', '科目', client)
            yitu.append('查询疾病所属科目')
    
    if "症状" in response:
        if '疾病' in entities:
            prompt += add_lianxi_prompt(entities['疾病'], '疾病的症状', '疾病症状', client)
            yitu.append('查询疾病的症状')
    
    if "治疗" in response:
        if '疾病' in entities:
            prompt += add_lianxi_prompt(entities['疾病'], '治疗的方法', '治疗方法', client)
            yitu.append('查询治疗的方法')
    
    if "并发" in response:
        if '疾病' in entities:
            prompt += add_lianxi_prompt(entities['疾病'], '疾病并发疾病', '疾病', client)
            yitu.append('查询疾病并发疾病')
    
    if "生产商" in response:
        try:
            sql_q = "match (a:药品商)-[r:生产]->(b:药品{名称:'%s'}) return a.名称" % (entities['药品'])
            res = client.run(sql_q).data()[0].values()
            prompt += f"<提示>"
            prompt += f"用户对{entities['药品']}可能有查询药品生产商的需求，知识图谱内容如下："
            if len(res) > 0:
                prompt += "".join(res)
            else:
                prompt += "图谱中无信息，查找失败"
            prompt += f"</提示>"
        except:
            pass
        yitu.append('查询药物生产商')
    
    # 如果没有查询到任何信息
    if pre_len == len(prompt):
        prompt += f"<提示>提示：知识库异常，没有相关信息！请你直接回答“根据已知信息无法回答该问题”！</提示>"
    
    # 添加用户问题和最终指令
    prompt += f"<用户问题>{query}</用户问题>"
    prompt += f"<注意>现在你已经知道给定的“<提示></提示>”和“<用户问题></用户问题>”了,你要极其认真的判断提示里是否有用户问题所需的信息，如果没有相关信息，你必须直接回答“根据已知信息无法回答该问题”。</注意>"

    prompt += f"<注意>你一定要再次检查你的回答是否完全基于“<提示></提示>”的内容，不可产生提示之外的答案！换而言之，你的任务是根据用户的问题，将“<提示></提示>”整理成有条理、有逻辑的语句。你起到的作用仅仅是整合提示的功能，你一定不可以利用自身已经存在的知识进行回答，你必须从提示中找到问题的答案！</注意>"
    prompt += f"<注意>你必须充分的利用提示中的知识，不可将提示中的任何信息遗漏，你必须做到对提示信息的充分整合。你回答的任何一句话必须在提示中有所体现！如果根据提示无法给出答案，你必须回答“根据已知信息无法回答该问题”。</注意>"
    
    print(f'prompt:{prompt}')
    return prompt, "、".join(yitu), entities