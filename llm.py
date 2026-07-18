import os
from langchain_aws import ChatBedrockConverse
from dotenv import load_dotenv

load_dotenv()

model = ChatBedrockConverse(
    region_name="us-east-1",
    # model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    model="us.anthropic.claude-sonnet-5",
    max_tokens=2048,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    # Enable Extended Thinking
    additional_model_request_fields={
        "thinking": {
            "type": "adaptive"
        },
        "output_config": {
            "effort": "low"  # or "low" or "medium"
        }
    }
)

def stream_thinking_only(prompt):
    """Stream only the thinking/reasoning tokens"""
    print("🤔 Thinking Process:\n")
    
    for chunk in model.stream(prompt):
        # chunk.content is a list of content blocks
        if isinstance(chunk.content, list):
            for block in chunk.content:
                if isinstance(block, dict):
                    # Filter for thinking content
                    if block.get('type') == 'thinking':
                        text = block.get('text', '')
                        if text:
                            print(text, end="", flush=True)
                    # Alternative for reasoning_content
                    elif block.get('type') == 'reasoning_content':
                        reasoning = block.get('reasoning_content', {})
                        if isinstance(reasoning, dict):
                            text = reasoning.get('text', '')
                            if text:
                                print(text, end="", flush=True)

def stream_text_only(prompt):
    """Stream only the text response (skip thinking)"""
    print("\n\n💬 Final Response:\n")
    
    for chunk in model.stream(prompt):
        if isinstance(chunk.content, list):
            for block in chunk.content:
                if isinstance(block, dict) and block.get('type') == 'text':
                    text = block.get('text', '')
                    if text:
                        print(text, end="", flush=True)

def stream_both_with_labels(prompt):
    """Stream thinking and text separately, with labels"""
    for chunk in model.stream(prompt):
        if isinstance(chunk.content, list):
            for block in chunk.content:
                if isinstance(block, dict):
                    if block.get('type') == 'thinking':
                        print(f"[THINKING] {block.get('text', '')}", end="", flush=True)
                    elif block.get('type') == 'text':
                        print(f"[RESPONSE] {block.get('text', '')}", end="", flush=True)

def main():
    prompt = "what's the current date and time?"
    
    # Option 1: Thinking only
    # stream_thinking_only(prompt)
    
    # Option 2: Text only
    stream_text_only(prompt)
    
    # Option 3: Both with labels
    # print("\n\n--- Combined Stream with Labels ---\n")
    # stream_both_with_labels(prompt)

if __name__ == "__main__":
    main()