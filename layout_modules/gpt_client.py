import os
import os.path as op
import json
import time
from openai import OpenAI
from utils import write_json

# Load environment variables from .env.local or .env file if available
try:
    from dotenv import load_dotenv
    # Debug: print current working directory
    current_dir = os.getcwd()
    print(f"Current working directory: {current_dir}")
    
    # Try .env.local first, then .env (look in project root)
    # Get script directory and go up to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # Go up one level from layout_modules
    
    env_local_path = os.path.join(project_root, '.env.local')
    env_path = os.path.join(project_root, '.env')
    
    if os.path.exists(env_local_path):
        print(f"Loading .env.local from: {env_local_path}")
        load_dotenv(env_local_path, override=True)  # Force override system env vars
    elif os.path.exists(env_path):
        print(f"Loading .env from: {env_path}")
        load_dotenv(env_path, override=True)  # Force override system env vars
    else:
        print(f"No .env.local or .env file found in project root: {project_root}")
except ImportError:
    print("python-dotenv not installed, using system environment variables")

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
    'gpt3.5-chat': 'gpt-3.5-turbo',
    'gpt4': 'gpt-4',
    'gpt-4.1': 'gpt-4.1',  # GPT-4.1是2025年最新模型
    'gpt-4-turbo': 'gpt-4-turbo',  # GPT-4 Turbo模型
    'gpt-4.5-preview': 'gpt-4.5-preview',  # GPT-4.5预览版模型
    'o3': 'o3',  # OpenAI o3推理模型，2025年4月发布
    'o4-mini': 'o4-mini',  # OpenAI o4-mini轻量级模型
}

# Models that use the new max_completion_tokens parameter instead of max_tokens
MODELS_WITH_NEW_TOKEN_PARAM = ['o4-mini', 'o3']

# Models that have restricted parameter support
MODELS_WITH_RESTRICTED_PARAMS = {
    'o4-mini': {
        'temperature': 1.0,  # Only supports default temperature
        'supports_custom_temperature': False,
        'unsupported_params': ['stop', 'frequency_penalty', 'presence_penalty', 'top_p', 'n'],  # Parameters not supported
        'supported_params': ['model', 'messages', 'temperature', 'max_completion_tokens']  # Only these are supported
    },
    'o3': {
        'temperature': 1.0,  # Only supports default temperature  
        'supports_custom_temperature': False,
        'unsupported_params': ['stop', 'frequency_penalty', 'presence_penalty', 'top_p', 'n'],  # Parameters not supported
        'supported_params': ['model', 'messages', 'temperature', 'max_completion_tokens']  # Only these are supported
    }
}


def call_gpt_api(prompt, args, val_id):
    """call GPT API"""
    # Debug print API key status
    api_key = os.getenv('OPENAI_API_KEY')
    organization = os.getenv('OPENAI_ORGANIZATION')
    print(f"API Key configured: {'Yes' if api_key else 'No'}")
    print(f"Organization configured: {'Yes' if organization else 'No'}")
    print(f"API Key: {api_key}")
    print(f"Organization: {organization}")
    gpt_name = GPT_NAME[args.gpt_type]
    
    # Sanitize gpt_type for file paths (replace dots with underscores)
    gpt_type_safe = args.gpt_type.replace('.', '_').replace('-', '_')
    
    # Check if response already exists
    cache_path = op.join(args.output_dir, 'tmp', gpt_type_safe, f"{val_id}.json")
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
            elif args.gpt_type in ['gpt3.5-chat', 'gpt4', 'gpt-4.1', 'gpt-4-turbo', 'gpt-4.5-preview', 'o3', 'o4-mini']:
                # Handle models with restricted parameter support
                if args.gpt_type in MODELS_WITH_RESTRICTED_PARAMS:
                    model_restrictions = MODELS_WITH_RESTRICTED_PARAMS[args.gpt_type]
                    
                    # Handle temperature restrictions
                    if not model_restrictions.get('supports_custom_temperature', True):
                        temperature = model_restrictions['temperature']
                        print(f"Note: {args.gpt_type} only supports temperature={temperature}, overriding user setting")
                    else:
                        temperature = args.temperature
                    
                    # Use only supported parameters for restricted models
                    print(f"Note: {args.gpt_type} has limited parameter support, using minimal parameter set")
                    api_params = {
                        'model': gpt_name,
                        'messages': prompt,
                        'temperature': temperature,
                        'max_completion_tokens': 1024 if args.room == 'livingroom' else 512,
                    }
                    
                    # Add n parameter only if supported (for multiple iterations)
                    if 'n' not in model_restrictions.get('unsupported_params', []):
                        api_params['n'] = args.n_iter
                    elif args.n_iter > 1:
                        print(f"Warning: {args.gpt_type} doesn't support multiple iterations (n={args.n_iter}), forcing n=1")
                        # Force single iteration for restricted models
                        args.n_iter = 1
                        
                else:
                    # Standard models use all parameters
                    max_token_param = 'max_completion_tokens' if args.gpt_type in MODELS_WITH_NEW_TOKEN_PARAM else 'max_tokens'
                    
                    api_params = {
                        'model': gpt_name,
                        'messages': prompt,
                        'temperature': args.temperature,
                        max_token_param: 1024 if args.room == 'livingroom' else 512,
                        'top_p': 1.0,
                        'frequency_penalty': 0.0,
                        'presence_penalty': 0.0,
                        'stop': "Condition:",
                        'n': args.n_iter,
                    }
                    
                    # 添加随机种子以确保每次调用都有不同结果
                    # 注意：不设置seed参数，让OpenAI使用随机种子
                
                response = client.chat.completions.create(**api_params)
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