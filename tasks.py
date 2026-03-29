import random
from faker import Faker

fake = Faker()


def generate_random_report(idx: str) -> dict:
    return {
        "id": idx,
        "sender": fake.company_email(),
        "subject": fake.catch_phrase(),
        "body": fake.paragraph(nb_sentences=3),
    }


def get_task_reports(task_id: int):
    from env import Report

    reports = []
    ground_truth = {}

    if task_id == 1:
        # Easy: IT Ticket Routing
        for _ in range(4):
            data = generate_random_report(str(fake.random_int(min=1000, max=9999)))
            reports.append(Report(**data))

        it_templates = [
            (
                "Login failure",
                "I can't log into the VPN. It keeps declining my password.",
            ),
            (
                "New mouse needed",
                "My mouse scroll wheel is completely broken. Can I request a replacement?",
            ),
            (
                "Software license",
                "My Adobe Creative Cloud license has expired. Who do I contact?",
            ),
            ("Printer issue", "The printer on the 3rd floor is jammed again."),
            (
                "Screen broken",
                "My monitor has a cracked screen after the move to the new office.",
            ),
            (
                "Laptop won't start",
                "My work laptop shows a black screen on boot. I've tried restarting.",
            ),
        ]
        chosen = random.sample(it_templates, 2)
        it_ids = []
        for sub, body in chosen:
            id_val = f"IT-{fake.random_int(min=1000, max=9999)}"
            it_ids.append(id_val)
            reports.append(
                Report(id=id_val, sender=fake.company_email(), subject=sub, body=body)
            )

        ground_truth["it_ids"] = it_ids

    elif task_id == 2:
        # Medium: Workplace Safety Violations
        for _ in range(3):
            data = generate_random_report(str(fake.random_int(min=1000, max=9999)))
            reports.append(Report(**data))

        deceptive = [
            (
                "Spilled coffee",
                f"Just totally soaked my new shirt with coffee next to {fake.name()}'s desk!",
            ),
            (
                "Unstable performance",
                "My emotional state has been very unstable since the Q3 earnings call.",
            ),
            ("Frayed nerves", "My nerves are totally frayed, I need a vacation!"),
            (
                "Slippery situation",
                f"Things have been getting very slippery between me and my manager {fake.name()}.",
            ),
        ]
        chosen_dec = random.sample(deceptive, 2)
        for sub, body in chosen_dec:
            reports.append(
                Report(
                    id=f"DEC-{fake.random_int(min=1000, max=9999)}",
                    sender=fake.company_email(),
                    subject=sub,
                    body=body,
                )
            )

        hazards = [
            (
                "Chemical Spill",
                f"There is an unidentified blue liquid spilling from a drum in sector {fake.bothify(text='?#')}.",
            ),
            (
                "Exposed Wiring",
                f"The server rack in room {fake.random_int(min=100, max=900)} has exposed, sparking wires.",
            ),
            (
                "Unstable scaffolding",
                "The temporary scaffolding near the main entrance is swaying dangerously in the wind.",
            ),
            (
                "Gas leak",
                f"There is a strong smell of gas near the kitchen on floor {fake.random_int(min=1, max=10)}. It's been there all morning.",
            ),
            (
                "Broken fire exit",
                "The fire exit door on the east wing is jammed shut and cannot be opened from the inside.",
            ),
        ]
        chosen_haz = random.sample(hazards, 2)
        hazard_ids = []
        for sub, body in chosen_haz:
            id_val = f"HAZ-{fake.random_int(min=1000, max=9999)}"
            hazard_ids.append(id_val)
            reports.append(
                Report(id=id_val, sender=fake.company_email(), subject=sub, body=body)
            )

        ground_truth["hazard_ids"] = hazard_ids

    elif task_id == 3:
        # Hard: Whistleblower Escalation
        for _ in range(7):
            data = generate_random_report(str(fake.random_int(min=1000, max=9999)))
            reports.append(Report(**data))

        gossip = [
            Report(
                id=f"GOS-{fake.random_int(1000, 9999)}",
                sender=fake.company_email(),
                subject="Did you hear?",
                body=f"I am almost 100% sure {fake.name()} is dating the new intern.",
            ),
            Report(
                id=f"GOS-{fake.random_int(1000, 9999)}",
                sender=fake.company_email(),
                subject="Secret",
                body=f"Please don't tell anybody, but I heard we might be getting acquired by {fake.company()}.",
            ),
        ]
        reports.extend(gossip)

        exec_name = fake.name()
        vendor = fake.company()
        amount = fake.random_int(min=50000, max=500000)
        w_id = f"WB-{fake.random_int(1000, 9999)}"
        reports.append(
            Report(
                id=w_id,
                sender=fake.free_email(),
                subject="Concerning behavior regarding financials",
                body=(
                    f"I wish to remain anonymous. I have found several unapproved payouts "
                    f"totaling ${amount:,} sent directly to '{vendor}', which is registered "
                    f"under {exec_name}'s spouse. This needs to be investigated immediately."
                ),
            )
        )
        ground_truth["whistleblower_id"] = w_id

    elif task_id == 4:
        # Medium-Hard: Legal Threat Routing
        # Agent must escalate genuine legal threats to the "Legal" team.
        # One borderline venting report acts as a false-positive trap.
        for _ in range(5):
            data = generate_random_report(str(fake.random_int(min=1000, max=9999)))
            reports.append(Report(**data))

        # Borderline / venting — should NOT be escalated
        venting_templates = [
            (
                "Fed up with management",
                f"I'm so frustrated. If things don't improve, I'm going to have to do something about {fake.name()}'s attitude. This is ridiculous!",
            ),
            (
                "Threatening to quit",
                "I swear, if I don't get a raise this quarter I am out of here. I've had enough of being underpaid.",
            ),
            (
                "Angry feedback",
                "I will not stand for this treatment. Someone needs to be held accountable for how I was spoken to in today's meeting.",
            ),
        ]
        venting_id = f"VENT-{fake.random_int(1000, 9999)}"
        chosen_vent = random.choice(venting_templates)
        reports.append(
            Report(
                id=venting_id,
                sender=fake.company_email(),
                subject=chosen_vent[0],
                body=chosen_vent[1],
            )
        )

        # Genuine legal threats — must be escalated to "Legal"
        legal_templates = [
            (
                "Notice of legal action",
                f"I have retained legal counsel and intend to file a formal lawsuit against the company for wrongful termination. My attorney, {fake.name()}, will be in contact within 5 business days.",
            ),
            (
                "Discrimination complaint — legal",
                f"After consulting with an employment lawyer, I am formally notifying HR that I will be filing a discrimination claim with the EEOC. This relates to the incident on {fake.date_this_year()}.",
            ),
            (
                "Sexual harassment — legal notice",
                "I have engaged a solicitor and will be pursuing legal action for the repeated harassment I have experienced. A formal letter will be sent to the company's registered address within 10 days.",
            ),
            (
                "Wage theft — attorney notice",
                f"My attorney has advised me that the unpaid overtime totaling ${fake.random_int(2000, 20000):,} constitutes wage theft under state law. We are prepared to file in small claims court.",
            ),
        ]
        chosen_legal = random.sample(legal_templates, 2)
        legal_ids = []
        for sub, body in chosen_legal:
            id_val = f"LEGAL-{fake.random_int(1000, 9999)}"
            legal_ids.append(id_val)
            reports.append(
                Report(id=id_val, sender=fake.free_email(), subject=sub, body=body)
            )

        ground_truth["legal_ids"] = legal_ids
        ground_truth["venting_id"] = venting_id

    elif task_id == 5:
        # Hard: Harassment Pattern Detection
        # Three reports from the same victim about the same harasser form a pattern.
        # Agent must flag all three as "urgent" AND assign to "HR_Investigation".
        # An isolated complaint and filler reports are distractors.
        for _ in range(5):
            data = generate_random_report(str(fake.random_int(min=1000, max=9999)))
            reports.append(Report(**data))

        # Isolated complaint — does NOT form a pattern, should be ignored
        isolated_id = f"ISO-{fake.random_int(1000, 9999)}"
        reports.append(
            Report(
                id=isolated_id,
                sender=fake.company_email(),
                subject="Rude colleague",
                body=f"{fake.name()} was very rude to me in the break room today. I'd appreciate some guidance on how to handle this.",
            )
        )

        # Pattern: same victim, same harasser across 3 separate reports
        victim_name = fake.name()
        victim_email = fake.free_email()
        harasser_name = fake.name()
        dates = [fake.date_this_month() for _ in range(3)]
        pattern_templates = [
            (
                "Uncomfortable workplace behaviour",
                f"I am writing again about {harasser_name}. On {dates[0]}, they made a comment about my appearance that made me deeply uncomfortable. I have raised this before but nothing has changed.",
            ),
            (
                "Follow-up: ongoing harassment",
                f"This is my second report regarding {harasser_name}. On {dates[1]}, they followed me to my car after work and asked for my personal number again. I feel unsafe.",
            ),
            (
                "Third report — urgent",
                f"I cannot stress enough how serious this has become. {harasser_name} has now begun sending messages to my personal social media. This is my third report. Please escalate this immediately. — {victim_name}",
            ),
        ]
        pattern_ids = []
        for sub, body in pattern_templates:
            id_val = f"PAT-{fake.random_int(1000, 9999)}"
            pattern_ids.append(id_val)
            reports.append(
                Report(id=id_val, sender=victim_email, subject=sub, body=body)
            )

        ground_truth["pattern_ids"] = pattern_ids
        ground_truth["isolated_id"] = isolated_id
        ground_truth["harasser_name"] = harasser_name

    random.shuffle(reports)
    return reports, ground_truth


def score_task(task_id: int, reports, last_action, history, ground_truth):

    if task_id == 1:
        it_ids = ground_truth.get("it_ids", [])
        it_moved = all(r.folder == "IT_Support" for r in reports if r.id in it_ids)
        non_it_safe = all(
            r.folder != "IT_Support" for r in reports if r.id not in it_ids
        )

        if it_moved and non_it_safe:
            return 1.0, "IT tickets routed correctly to IT_Support.", True
        elif (
            len([h for h in history if h["action"]["action_type"] == "move"])
            >= len(it_ids) + 1
        ):
            if not non_it_safe:
                return 0.0, "Routed a non-IT ticket to IT_Support.", True
            elif not it_moved:
                return 0.5, "Missed some IT tickets.", True

        if len(history) > 15:
            return 0.0, "Max steps reached without success.", True

        return 0.0, "", False

    elif task_id == 2:
        hazard_ids = ground_truth.get("hazard_ids", [])
        real_tagged = all(
            "safety_hazard" in r.tags for r in reports if r.id in hazard_ids
        )
        real_replied = all(r.replied for r in reports if r.id in hazard_ids)
        false_tagged = any(
            "safety_hazard" in r.tags for r in reports if r.id not in hazard_ids
        )

        if false_tagged:
            return 0.0, "FAILED: False positive tagged as safety hazard.", True

        if real_tagged and real_replied:
            return 1.0, "All genuine safety hazards tagged and replied to.", True

        if len(history) > 15:
            tags_got = sum(
                1 for r in reports if r.id in hazard_ids and "safety_hazard" in r.tags
            )
            return max(0.0, tags_got * 0.4), "Timeout reached.", True

        return (
            sum(1 for r in reports if r.id in hazard_ids and "safety_hazard" in r.tags)
            * 0.25,
            "",
            False,
        )

    elif task_id == 3:
        wb_id = ground_truth.get("whistleblower_id")
        whistleblower = next((r for r in reports if r.id == wb_id), None)

        bad_escalations = any(
            (r.folder.lower() == "confidential" or "investigation_required" in r.tags)
            for r in reports
            if r.id != wb_id
        )
        if bad_escalations:
            return (
                0.0,
                "FAILED: Escalated or tagged non-whistleblower reports incorrectly.",
                True,
            )

        if not whistleblower:
            return 0.0, "Error: whistleblower report missing.", True

        moved_correctly = whistleblower.folder == "Confidential"
        tagged_correctly = "investigation_required" in whistleblower.tags

        score = 0.0
        if moved_correctly:
            score += 0.5
        if tagged_correctly:
            score += 0.5

        if score == 1.0:
            return 1.0, "Perfectly handled whistleblower complaint.", True

        if len(history) > 15:
            return score, "Out of steps.", True

        return score, "", False

    elif task_id == 4:
        legal_ids = ground_truth.get("legal_ids", [])
        venting_id = ground_truth.get("venting_id")

        # Immediate fail: venting report wrongly escalated to Legal
        venting_report = next((r for r in reports if r.id == venting_id), None)
        if venting_report and venting_report.escalated_to == "Legal":
            return (
                0.0,
                "FAILED: Venting/non-legal report wrongly escalated to Legal.",
                True,
            )

        legal_escalated = [
            r for r in reports if r.id in legal_ids and r.escalated_to == "Legal"
        ]
        n_correct = len(legal_escalated)
        n_total = len(legal_ids)

        # Partial credit: 0.5 per correctly escalated legal report
        score = (n_correct / n_total) * 1.0 if n_total else 0.0

        if n_correct == n_total:
            return 1.0, "All legal threats correctly escalated to the Legal team.", True

        if len(history) > 20:
            return score, "Out of steps.", True

        # Continuous signal: proportion escalated so far
        return score * 0.5, "", False

    elif task_id == 5:
        pattern_ids = ground_truth.get("pattern_ids", [])
        isolated_id = ground_truth.get("isolated_id")

        # Immediate fail: isolated complaint wrongly acted on as pattern
        isolated = next((r for r in reports if r.id == isolated_id), None)
        if isolated and (
            isolated.priority == "urgent" or isolated.assigned_to == "HR_Investigation"
        ):
            return (
                0.0,
                "FAILED: Isolated complaint incorrectly treated as a harassment pattern.",
                True,
            )

        pattern_reports = [r for r in reports if r.id in pattern_ids]

        # Each pattern report needs: priority=urgent AND assigned_to=HR_Investigation
        fully_handled = [
            r
            for r in pattern_reports
            if r.priority == "urgent" and r.assigned_to == "HR_Investigation"
        ]
        partially_handled = [
            r
            for r in pattern_reports
            if r.priority == "urgent" or r.assigned_to == "HR_Investigation"
        ]

        n_full = len(fully_handled)
        n_partial = len(partially_handled)
        n_total = len(pattern_ids)

        score = (
            (n_full / n_total) * 0.8 + (n_partial / n_total) * 0.2 if n_total else 0.0
        )

        if n_full == n_total:
            return (
                1.0,
                "All harassment pattern reports correctly flagged urgent and assigned.",
                True,
            )

        if len(history) > 25:
            return round(score, 2), "Out of steps.", True

        # Continuous signal
        return round(score * 0.6, 2), "", False

    return 0.0, "Unknown task.", True
