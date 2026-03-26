import re

def get_task_reports(task_id: int):
    from env import Report
    if task_id == 1:
        return [
            Report(id="101", sender="b.smith@corp.com", subject="My monitor", body="My monitor won't turn on. Please help."),
            Report(id="102", sender="j.doe@corp.com", subject="Complaint regarding lunch", body="Someone keeps stealing my sandwich from the fridge."),
            Report(id="103", sender="admin@corp.com", subject="Password expired", body="I need a password reset for my primary account.")
        ]
    elif task_id == 2:
        return [
            Report(id="201", sender="worker1@corp.com", subject="Incident in wing B", body="There is a large chemical spill in the hallway of Wing B. We need a cleanup crew."),
            Report(id="202", sender="accounting@corp.com", subject="Coffee", body="I spilled coffee on my shirt this morning, how embarrassing!"),
            Report(id="203", sender="worker2@corp.com", subject="Warehouse issue", body="The shelves in aisle 4 are extremely unstable and swaying."),
            Report(id="204", sender="manager@corp.com", subject="Stress", body="My emotions have been very unstable recently due to project deadlines.")
        ]
    elif task_id == 3:
        return [
            Report(id="301", sender="anonymous@corp.com", subject="Concerning behavior", body="I've noticed Jane from accounting driving a new Ferrari and there are some huge unexplained vendor payouts to 'ABC Consulting'. I think she might be embezzling funds."),
            Report(id="302", sender="office.gossip@corp.com", subject="Did you hear?", body="I heard Bob and Alice are dating. They were seen at a restaurant together."),
            Report(id="303", sender="j.smith@corp.com", subject="Expense report", body="Attached is my expense report for the conference in Vegas."),
        ]
    return []

def score_task(task_id: int, reports, last_action, history):
    if task_id == 1:
        it_ids = ["101", "103"]
        non_it_ids = ["102"]
        
        it_moved = all(r.folder == "IT_Support" for r in reports if r.id in it_ids)
        non_it_safe = all(r.folder != "IT_Support" for r in reports if r.id in non_it_ids)
        
        if it_moved and non_it_safe:
            return 1.0, "IT tickets routed correctly.", True
        elif len([h for h in history if h['action']['action_type'] == 'move']) >= 3:
            if not non_it_safe:
                return 0.0, "Routed a non-IT ticket to IT_Support.", True
            elif not it_moved:
                return 0.5, "Missed some IT tickets.", True
                
        if len(history) > 10:
            return 0.0, "Max steps reached without success.", True
            
        return 0.0, "", False
        
    elif task_id == 2:
        hazard_ids = ["201", "203"]
        false_ids = ["202", "204"]
        
        real_tagged = all("safety_hazard" in r.tags for r in reports if r.id in hazard_ids)
        real_replied = all(r.replied for r in reports if r.id in hazard_ids)
        
        false_tagged = any("safety_hazard" in r.tags for r in reports if r.id in false_ids)
        
        if false_tagged:
            return 0.0, "FAILED: False positive tagged as safety hazard.", True
            
        if real_tagged and real_replied:
            return 1.0, "All genuine safety hazards tagged and replied to.", True
            
        if len(history) > 15:
            tags_got = sum(1 for r in reports if r.id in hazard_ids and "safety_hazard" in r.tags)
            return tags_got * 0.5, "Timeout reached.", True
            
        return sum(1 for r in reports if r.id in hazard_ids and "safety_hazard" in r.tags) * 0.25, "", False

    elif task_id == 3:
        whistleblower = next((r for r in reports if r.id == "301"), None)
        gossip = next((r for r in reports if r.id == "302"), None)
        
        if gossip and (gossip.folder.lower() == "Confidential" or "investigation_required" in gossip.tags):
            return 0.0, "FAILED: Escalated basic office gossip.", True
            
        moved_correctly = whistleblower.folder == 'Confidential'
        tagged_correctly = "investigation_required" in whistleblower.tags
        
        score = 0.0
        if moved_correctly: score += 0.5
        if tagged_correctly: score += 0.5
        
        if score == 1.0:
            return 1.0, "Perfectly handled whistleblower complaint.", True
            
        if len(history) > 10:
            return score, "Out of steps.", True
            
        return score, "", False
        
    return 0.0, "Unknown task.", True
