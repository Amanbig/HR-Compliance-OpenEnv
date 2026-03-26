import re

def get_task_emails(task_id: int):
    from env import Email
    if task_id == 1:
        return [
            Email(id="1", sender="boss@corp.com", subject="Meeting", body="Let's meet at 10 AM."),
            Email(id="2", sender="spam@offers.com", subject="WIN LOTTERY", body="Click here to win big!"),
            Email(id="3", sender="friend@mail.com", subject="Lunch", body="Are we still on for lunch?")
        ]
    elif task_id == 2:
        return [
            Email(id="1", sender="user@client.com", subject="System Down", body="The server is completely down ASAP!"),
            Email(id="2", sender="boss@corp.com", subject="Update", body="Weekly update looks good."),
            Email(id="3", sender="dev@corp.com", subject="Broken build", body="The main branch is broken.")
        ]
    elif task_id == 3:
        return [
            Email(id="1", sender="angry@customer.com", subject="Refund please", body="I am not happy with my purchase. How do I get a refund?"),
            Email(id="2", sender="friend@mail.com", subject="Hey", body="What's up?"),
        ]
    return []

def score_task(task_id: int, emails, last_action, history):
    if task_id == 1:
        spam_deleted = all(e.folder == 'trash' for e in emails if 'spam' in e.sender)
        others_safe = all(e.folder != 'trash' for e in emails if 'spam' not in e.sender)
        
        if spam_deleted and others_safe:
            return 1.0, "Spam correctly deleted.", True
        elif len([h for h in history if h['action']['action_type'] == 'delete']) >= 1:
            if not others_safe:
                return 0.0, "Deleted a legitimate email.", True
                
        if len(history) > 10:
            return 0.0, "Max steps reached without success.", True
            
        return 0.0, "", False
        
    elif task_id == 2:
        urgent_keywords = ["asap", "down", "broken"]
        
        correct_tags = 0
        total_urgent = 0
        false_positives = 0
        
        for e in emails:
            is_urgent_text = any(kw in e.body.lower() or kw in e.subject.lower() for kw in urgent_keywords)
            has_urgent_tag = 'urgent' in e.tags
            
            if is_urgent_text:
                total_urgent += 1
                if has_urgent_tag:
                    correct_tags += 1
            else:
                if has_urgent_tag:
                    false_positives += 1
                    
        if correct_tags == total_urgent and false_positives == 0:
            return 1.0, "Correctly tagged all urgent emails.", True
            
        if len(history) > 10:
            score = max(0.0, (correct_tags / total_urgent if total_urgent > 0 else 0) - (0.2 * false_positives))
            return score, "Max steps reached.", True
            
        return max(0.0, correct_tags / (total_urgent if total_urgent > 0 else 1)), "", False

    elif task_id == 3:
        refund_email = next((e for e in emails if e.id == "1"), None)
        if not refund_email:
            return 0.0, "Refund email missing.", True
            
        moved_correctly = refund_email.folder.lower() == 'refunds'
        replied_correctly = refund_email.replied and "policy" in (refund_email.reply_body or "").lower()
        
        score = 0.0
        if moved_correctly: score += 0.5
        if replied_correctly: score += 0.5
        
        if moved_correctly and replied_correctly:
            return 1.0, "Handled refund request perfectly.", True
            
        if len(history) > 10:
            return score, "Out of steps.", True
            
        return score, "", False
        
    return 0.0, "Unknown task.", True
