import random
from faker import Faker

fake = Faker()

def generate_random_report(idx: str) -> dict:
    return {
        "id": idx,
        "sender": fake.company_email(),
        "subject": fake.catch_phrase(),
        "body": fake.paragraph(nb_sentences=3)
    }

def get_task_reports(task_id: int):
    from env import Report
    reports = []
    ground_truth = {}
    
    if task_id == 1:
        for _ in range(4):
            data = generate_random_report(str(fake.random_int(min=1000, max=9999)))
            reports.append(Report(**data))
            
        it_templates = [
            ("Login failure", "I can't log into the VPN. It keeps declining my password."),
            ("New mouse needed", "My mouse scroll wheel is completely broken. Can I request a replacement?"),
            ("Software license", "My Adobe Creative Cloud license has expired. Who do I contact?"),
            ("Printer issue", "The printer on the 3rd floor is jammed again.")
        ]
        chosen = random.sample(it_templates, 2)
        it_ids = []
        for i, (sub, body) in enumerate(chosen):
            id_val = f"IT-{fake.random_int(min=1000, max=9999)}"
            it_ids.append(id_val)
            reports.append(Report(
                id=id_val,
                sender=fake.company_email(),
                subject=sub,
                body=body
            ))
            
        ground_truth['it_ids'] = it_ids
        
    elif task_id == 2:
        for _ in range(3):
            data = generate_random_report(str(fake.random_int(min=1000, max=9999)))
            reports.append(Report(**data))
            
        deceptive = [
            ("Spilled coffee", f"Just totally soaked my new shirt with coffee next to {fake.name()}'s desk!"),
            ("Unstable performance", f"My emotional state has been very unstable since the Q3 earnings call."),
            ("Frayed nerves", "My nerves are totally frayed, I need a vacation!")
        ]
        chosen_dec = random.sample(deceptive, 2)
        for i, (sub, body) in enumerate(chosen_dec):
            reports.append(Report(
                id=f"DEC-{fake.random_int(min=1000, max=9999)}", sender=fake.company_email(), subject=sub, body=body
            ))
            
        hazards = [
            ("Chemical Spill", f"There is an unidentified blue liquid spilling from a drum in sector {fake.bothify(text='?#')}."),
            ("Exposed Wiring", f"The server rack in room {fake.random_int(min=100, max=900)} has exposed, sparking wires."),
            ("Unstable scaffolding", "The temporary scaffolding near the main entrance is swaying dangerously in the wind.")
        ]
        chosen_haz = random.sample(hazards, 2)
        hazard_ids = []
        for i, (sub, body) in enumerate(chosen_haz):
            id_val = f"HAZ-{fake.random_int(min=1000, max=9999)}"
            hazard_ids.append(id_val)
            reports.append(Report(id=id_val, sender=fake.company_email(), subject=sub, body=body))
            
        ground_truth['hazard_ids'] = hazard_ids

    elif task_id == 3:
        for _ in range(7):
            data = generate_random_report(str(fake.random_int(min=1000, max=9999)))
            reports.append(Report(**data))
            
        gossip = [
            Report(id=f"GOS-{fake.random_int(1000,9999)}", sender=fake.company_email(), subject="Did you hear?", body=f"I am almost 100% sure {fake.name()} is dating the new intern."),
            Report(id=f"GOS-{fake.random_int(1000,9999)}", sender=fake.company_email(), subject="Secret", body=f"Please don't tell anybody, but I heard we might be getting acquired by {fake.company()}.")
        ]
        reports.extend(gossip)
        
        exec_name = fake.name()
        vendor = fake.company()
        amount = fake.random_int(min=50000, max=500000)
        w_id = f"WB-{fake.random_int(1000,9999)}"
        reports.append(Report(
            id=w_id,
            sender=fake.free_email(),
            subject="Concerning behavior regarding financials",
            body=f"I wish to remain anonymous. I have found several unapproved payouts totaling ${amount} sent directly to '{vendor}', which is registered under {exec_name}'s spouse. This needs to be investigated immediately."
        ))
        ground_truth['whistleblower_id'] = w_id

    random.shuffle(reports)
    return reports, ground_truth

def score_task(task_id: int, reports, last_action, history, ground_truth):
    if task_id == 1:
        it_ids = ground_truth.get('it_ids', [])
        
        it_moved = all(r.folder == "IT_Support" for r in reports if r.id in it_ids)
        non_it_safe = all(r.folder != "IT_Support" for r in reports if r.id not in it_ids)
        
        if it_moved and non_it_safe:
            return 1.0, "IT tickets routed correctly to IT_Support.", True
        elif len([h for h in history if h['action']['action_type'] == 'move']) >= len(it_ids) + 1:
            if not non_it_safe:
                return 0.0, "Routed a non-IT ticket to IT_Support.", True
            elif not it_moved:
                return 0.5, "Missed some IT tickets.", True
                
        if len(history) > 15:
            return 0.0, "Max steps reached without success.", True
            
        return 0.0, "", False
        
    elif task_id == 2:
        hazard_ids = ground_truth.get('hazard_ids', [])
        
        real_tagged = all("safety_hazard" in r.tags for r in reports if r.id in hazard_ids)
        real_replied = all(r.replied for r in reports if r.id in hazard_ids)
        
        false_tagged = any("safety_hazard" in r.tags for r in reports if r.id not in hazard_ids)
        
        if false_tagged:
            return 0.0, "FAILED: False positive tagged as safety hazard.", True
            
        if real_tagged and real_replied:
            return 1.0, "All genuine safety hazards tagged and replied to.", True
            
        if len(history) > 15:
            tags_got = sum(1 for r in reports if r.id in hazard_ids and "safety_hazard" in r.tags)
            return max(0.0, tags_got * 0.4), "Timeout reached.", True
            
        return sum(1 for r in reports if r.id in hazard_ids and "safety_hazard" in r.tags) * 0.25, "", False

    elif task_id == 3:
        wb_id = ground_truth.get('whistleblower_id')
        whistleblower = next((r for r in reports if r.id == wb_id), None)
        
        bad_escalations = any(
            (r.folder.lower() == "confidential" or "investigation_required" in r.tags) 
            for r in reports if r.id != wb_id
        )
        if bad_escalations:
            return 0.0, "FAILED: Escalated or tagged non-whistleblower emails incorrectly.", True
            
        if not whistleblower:
            return 0.0, "Error: WB missing.", True
            
        moved_correctly = whistleblower.folder == 'Confidential'
        tagged_correctly = "investigation_required" in whistleblower.tags
        
        score = 0.0
        if moved_correctly: score += 0.5
        if tagged_correctly: score += 0.5
        
        if score == 1.0:
            return 1.0, "Perfectly handled whistleblower complaint.", True
            
        if len(history) > 15:
            return score, "Out of steps.", True
            
        return score, "", False
        
    return 0.0, "Unknown task.", True
