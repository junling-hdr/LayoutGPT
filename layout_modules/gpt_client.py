import os
import os.path as op
import json
import time
from openai import OpenAI
from utils import write_json

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system environment variables

# Initialize OpenAI client (new v1.0+ API) - Load from environment variables
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    organization=os.getenv('OPENAI_ORGANIZATION')
)

# Check if API key is properly configured
if not client.api_key:
    print("Warning: OPENAI_API_KEY environment variable is not set.")
    print("Please set your OpenAI API key in environment variables:")
    print("export OPENAI_API_KEY='your_api_key_here'")
    print("export OPENAI_ORGANIZATION='your_org_id_here'  # optional") 

# GPT Type mapping
GPT_NAME = {
    'gpt3.5': 'text-davinci-003',
    'gpt3.5-chat': 'gpt-3.5-turbo',
    'gpt4': 'gpt-4',
}


def call_gpt_api(prompt, args, val_id):
    """调用GPT API"""
    gpt_name = GPT_NAME[args.gpt_type]
    
    # Check if response already exists
    cache_path = op.join(args.output_dir, 'tmp', args.gpt_type, f"{val_id}.json")
    if op.exists(cache_path):
        return json.load(open(cache_path))

    while True:
        try:
            if args.gpt_type == 'gpt3.5':
                response = client.completions.create(
                    model=gpt_name,
                    prompt=prompt,
                    temperature=args.temperature,
                    max_tokens=1024 if args.room == 'livingroom' else 512,
                    top_p=1.0,
                    frequency_penalty=0.0,
                    presence_penalty=0.0,
                    stop="Condition:",
                    n=args.n_iter,
                )
            elif args.gpt_type in ['gpt3.5-chat', 'gpt4']:
                response = client.chat.completions.create(
                    model=gpt_name,
                    messages=prompt,
                    temperature=0.7,
                    max_tokens=1024 if args.room == 'livingroom' else 512,
                    top_p=1.0,
                    frequency_penalty=0.0,
                    presence_penalty=0.0,
                    stop="Condition:",
                    n=args.n_iter,
                )
            else:
                raise NotImplementedError
            
            # Convert response to dict for compatibility with old code
            response = response.model_dump()
            
            # Cache the response
            os.makedirs(op.dirname(cache_path), exist_ok=True)
            write_json(cache_path, response)
            
            return response
            
        except Exception as e:
            error_type = type(e).__name__
            if 'ServiceUnavailable' in error_type or 'InternalServerError' in error_type:
                print('OpenAI ServiceUnavailableError.\tWill try again in 5 seconds.')
                time.sleep(5)
            elif 'RateLimit' in error_type:
                print('OpenAI RateLimitError.\tWill try again in 5 seconds.')
                time.sleep(5)
            elif 'InvalidRequest' in error_type or 'BadRequest' in error_type:
                print(e)
                print('Input too long. Will shrink the prompting examples.')
                raise e  # Let the caller handle this
            elif 'APIError' in error_type:
                print('OpenAI API Error.\tWill try again in 5 seconds.')
                time.sleep(5)
            else:
                print(f'Unexpected error: {e}')
                time.sleep(5) 