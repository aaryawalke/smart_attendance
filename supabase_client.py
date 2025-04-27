from supabase import create_client, Client
from dotenv import load_dotenv
import os

# Load environment variables from a .env file
load_dotenv()

# Get the variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Create the Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
