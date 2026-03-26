# OpenEnv: Email Triage

## Environment Motivation & Description
The **Email Triage** environment simulates a common, real-world task performed by administrative assistants and customer support agents: managing an active inbox. Tasks involve reading emails, moving spam to the trash, tagging urgent messages, and responding to specific customer inquiries. This environment challenges AI agents to understand natural language intent, select appropriate actions, and complete workflows.

## Configuration & Specifications
This environment is compliant with the OpenEnv specification, modeling `Observation`, `Action`, and `Reward` using **Pydantic**. 

### Observation Space
The initial state and observations are returned as an `Observation` struct:
```python
class Email(BaseModel):
    id: str
    sender: str
    subject: str
    body: str
    folder: str
    tags: List[str]
    read: bool
    replied: bool
    reply_body: Optional[str]

class Observation(BaseModel):
    emails: List[Email]
    current_folder: str
```

### Action Space
Agents must return valid JSON that conforms to the `Action` structure to interact with the environment:
```python
class Action(BaseModel):
    action_type: Literal['read', 'reply', 'move', 'delete', 'tag']
    email_id: str
    payload: Optional[str] = None
```

### Reward Function
The `Reward` struct returns rich details instead of simple float boundaries:
- `value`: Final calculated task score (`0.0 - 1.0`).
- `partial_progress`: Fractional points given for moving the state forward (e.g. tagging a single email correctly).
- `penalties`: Deductions for invalid actions (e.g., replying without a payload).
- `reason`: A textual description explaining the step's reward.

## Tasks
The agent is tested across 3 distinct tasks of increasing difficulty:
1. **Easy:** Delete spam emails. (*Score: 1.0 for deleting only spam emails, 0.0 otherwise*).
2. **Medium:** Tag urgent emails. Agent must read subject lines and bodies and tag emails mentioning "ASAP", "down", or "broken" with the word `urgent`. (*Score: percentage of correctly identified emails minus false positives*).
3. **Hard:** Handle refunds. Identify complaints and refund requests, move them to the "Refunds" folder, and reply quoting the refund "policy". (*Score: 0.5 points for moving, 0.5 points for proper reply*).

## Setup & Execution

### Running the Python Baseline
An evaluation script (`baseline.py`) uses the OpenAI Python SDK and `gpt-4o` to attempt the tasks.

1. Install dependencies (we recommend `uv` for ultra-fast installs):
    ```bash
    pip install uv
    uv pip install -e .
    ```
2. Set your OpenAI key:
    ```bash
    export OPENAI_API_KEY="sk-proj-..."
    # Optional: for alternative/local endpoints
    export OPENAI_BASE_URL="http://localhost:8000/v1" 
    export OPENAI_MODEL="meta-llama/Llama-3-70b-chat-hf"
    ```
 3. Run:
    ```bash
   python baseline.py
   ```

### Running on Docker / Hugging Face Spaces
This app includes a UI powered by Gradio to let you test agent interactions manually.

#### via Docker
```bash
docker build -t openenv-email .
docker run -p 7860:7860 openenv-email
```
Open `http://localhost:7860`.

#### via Hugging Face Spaces
Simply push this directory to a Hugging Face Space using the Docker SDK.

## Baseline Scores (gpt-4o)
- **Task 1 (Easy):** 1.0
- **Task 2 (Medium):** 1.0
- **Task 3 (Hard):** 1.0
