def add_score(category_data, rule_map, check_name, earned, max_points_override=None, issue_msg=None, success_msg=None, is_penalty=False):
    rule = rule_map.get(check_name, {"max_points": 0, "weight": 1})
    max_p = max_points_override if max_points_override is not None else rule.get("max_points", 0)
    actual_earned = (max_p - earned) if is_penalty else earned
    category_data["earned_points"] += actual_earned * rule.get("weight", 1)
    category_data["max_points"] += max_p * rule.get("weight", 1)
    title_cased_check_name = check_name.replace('_score','').replace('_penalty','').replace('_',' ').title()
    if is_penalty:
        if earned > 0 and issue_msg:
            category_data["issues"].append(f"{title_cased_check_name}: {issue_msg} (Penalty: {earned:.1f}/{max_p:.1f})")
        elif success_msg:
            category_data["successes"].append(f"{title_cased_check_name}: {success_msg} (Score: {max_p:.1f}/{max_p:.1f})")
    else:
        if earned < max_p * 0.8 and issue_msg:
            category_data["issues"].append(f"{title_cased_check_name}: {issue_msg} (Score: {earned:.1f}/{max_p:.1f})")
        elif earned >= max_p * 0.8 and success_msg:
            category_data["successes"].append(f"{title_cased_check_name}: {success_msg} (Score: {earned:.1f}/{max_p:.1f})")

