import discord
from discord.ext import commands
import os
import random
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.members = True  # Need this for handling member join events
intents.message_content = True  # Need this for handling message content

bot = commands.Bot(command_prefix='!', intents=intents)

# Store verification codes temporarily (in production, consider using a database)
verification_data = {}  # Format: {user_id: {"email": email, "code": code}}

# Keep track of last email request time (for cooldown)
last_email_request_time = {}  # Format: {user_id: timestamp}

# Load environment variables

# Discord bot token and email configuration
TOKEN = os.getenv('DISCORD_TOKEN')

# SMTP Email Configuration
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
EMAIL_FROM = os.getenv('EMAIL_FROM', 'noreply@yourdomain.com')
EMAIL_FROM_NAME = os.getenv('EMAIL_FROM_NAME', 'Discord Verification')

# Email domain restriction (optional)
ALLOWED_EMAIL_DOMAINS = os.getenv('ALLOWED_EMAIL_DOMAINS', '').split(',')
RESTRICT_TO_DOMAINS = os.getenv('RESTRICT_TO_DOMAINS', 'false').lower() == 'true'

# Specific server to operate on
TARGET_GUILD_ID = int(os.getenv('TARGET_GUILD_ID'))

# Role ID to assign after verification
VERIFIED_ROLE_ID = int(os.getenv('VERIFIED_ROLE_ID'))

# Channel ID for admin logs
ADMIN_LOG_CHANNEL_ID = int(os.getenv('ADMIN_LOG_CHANNEL_ID'))

# Cooldown time in seconds, defaults to 180 if not provided
COOLDOWN_TIME = int(os.getenv('EMAIL_COOLDOWN_SECONDS', '180'))

@bot.event
async def on_ready():
    print(f'{bot.user.name} is connected to Discord!')
    
    # Set up admin log channel
    global admin_log_channel
    admin_log_channel = bot.get_channel(ADMIN_LOG_CHANNEL_ID)
    if not admin_log_channel:
        print(f"Warning: Admin log channel with ID {ADMIN_LOG_CHANNEL_ID} not found!")
        
    # Log email domain restriction status
    if RESTRICT_TO_DOMAINS and ALLOWED_EMAIL_DOMAINS:
        print(f"Email domain restriction enabled. Allowed domains: {', '.join(ALLOWED_EMAIL_DOMAINS)}")
        if admin_log_channel:
            await admin_log_channel.send(f"Bot started with email domain restriction enabled. Allowed domains: {', '.join(ALLOWED_EMAIL_DOMAINS)}")
    else:
        print("Email domain restriction disabled. All email domains allowed.")
        if admin_log_channel:
            await admin_log_channel.send("Bot started with email domain restriction disabled. All email domains allowed.")

@bot.event
async def on_member_join(member):
    """Send a DM to new members with instructions for verification"""
    # Check if the member joined the target guild
    if member.guild.id != TARGET_GUILD_ID:
        return
        
    try:
        # Create an embed for a nicer looking message
        embed = discord.Embed(
            title="Welcome to the Server!",
            description="To gain access, please verify your email address.",
            color=discord.Color.blue()
        )
        embed.add_field(name="How to verify:", value="Click the button below to start the verification process.")
        
        # Create a button for email verification
        verify_button = discord.ui.Button(label="Verify Email", style=discord.ButtonStyle.primary, custom_id="verify_email")
        
        # Create a view and add the button
        view = discord.ui.View()
        view.add_item(verify_button)
        
        # Send the message with the button
        await member.send(embed=embed, view=view)
        
        # Log to admin channel
        if admin_log_channel:
            await admin_log_channel.send(f"New member joined: {member.mention} ({member.id}). Verification DM sent.")
    
    except discord.Forbidden:
        # If the user has DMs disabled
        if admin_log_channel:
            await admin_log_channel.send(f"Failed to send verification DM to {member.mention} ({member.id}). User may have DMs disabled.")

class EmailModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.add_item(discord.ui.TextInput(
            label="Email Address",
            placeholder="Enter your email address",
            custom_id="email_input",
            min_length=5,
            max_length=100
        ))
    
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True)

        email = self.children[0].value
        user_id = interaction.user.id
        
        # 1) Check if user already has Verified role
        guild = bot.get_guild(TARGET_GUILD_ID)
        if guild:
            member = guild.get_member(user_id)
            if member:
                verified_role = guild.get_role(VERIFIED_ROLE_ID)
                if verified_role in member.roles:
                    embed = discord.Embed(
                        title="Already Verified",
                        description="You already have the Verified role. No need to verify again!",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
        
        # 2) Check cooldown
        now = time.time()
        if user_id in last_email_request_time:
            elapsed = now - last_email_request_time[user_id]
            if elapsed < COOLDOWN_TIME:
                time_left = int(COOLDOWN_TIME - elapsed)
                embed = discord.Embed(
                    title="Cooldown Active",
                    description=f"You must wait {time_left} more seconds before requesting another email.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
        
        # Update the last request time
        last_email_request_time[user_id] = now
        
        # 3) Check email domain restriction
        if RESTRICT_TO_DOMAINS and ALLOWED_EMAIL_DOMAINS:
            email_domain = email.split('@')[-1].lower()
            if email_domain not in [domain.lower().strip() for domain in ALLOWED_EMAIL_DOMAINS]:
                embed = discord.Embed(
                    title="Invalid Email Domain",
                    description=f"Sorry, but verification is restricted to the following email domains: {', '.join(ALLOWED_EMAIL_DOMAINS)}",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Log to admin channel
                if admin_log_channel:
                    await admin_log_channel.send(f"User {interaction.user.mention} ({user_id}) attempted to verify with an unauthorized email domain: {email_domain}")
                return
        
        # 4) Generate a 6-digit verification code
        verification_code = ''.join(random.choices('0123456789', k=6))
        
        # Store the email and code
        verification_data[user_id] = {
            "email": email,
            "code": verification_code
        }
        
        # Send email with verification code
        success = send_verification_email(email, verification_code)
        
        if success:
            embed = discord.Embed(
                title="Verification Email Sent!",
                description=f"We've sent a 6-digit verification code to {email}. Please check your inbox (and spam folder).",
                color=discord.Color.green()
            )
            
            # Create a button to enter verification code
            verify_code_button = discord.ui.Button(
                label="Enter Verification Code", 
                style=discord.ButtonStyle.primary, 
                custom_id="enter_code"
            )
            
            view = discord.ui.View()
            view.add_item(verify_code_button)
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
            # Log to admin channel
            if admin_log_channel:
                await admin_log_channel.send(f"Verification email sent to {email} for user {interaction.user.mention} ({user_id})")
        else:
            embed = discord.Embed(
                title="Error",
                description="Failed to send verification email. Please try again or contact an admin.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

class CodeVerificationModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.add_item(discord.ui.TextInput(
            label="Verification Code",
            placeholder="Enter the 6-digit code from your email",
            custom_id="code_input",
            min_length=6,
            max_length=6
        ))
    
    async def on_submit(self, interaction):
        entered_code = self.children[0].value
        user_id = interaction.user.id
        
        # Check if the user has a pending verification
        if user_id not in verification_data:
            embed = discord.Embed(
                title="Error",
                description="No verification in progress. Please start over.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if the code matches
        if verification_data[user_id]["code"] == entered_code:
            # Find the target guild
            guild = bot.get_guild(TARGET_GUILD_ID)
            if not guild:
                embed = discord.Embed(
                    title="Error",
                    description="Could not find the target server. Please contact an admin.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            member = guild.get_member(user_id)
            if not member:
                embed = discord.Embed(
                    title="Error",
                    description="Could not find your membership. Please contact an admin.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            if not member:
                embed = discord.Embed(
                    title="Error",
                    description="Could not find your membership. Please contact an admin.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Assign the verified role
            try:
                verified_role = guild.get_role(VERIFIED_ROLE_ID)
                if not verified_role:
                    # Log error but continue
                    if admin_log_channel:
                        await admin_log_channel.send(f"Error: Verified role with ID {VERIFIED_ROLE_ID} not found!")
                else:
                    await member.add_roles(verified_role)
                
                # Send success message
                embed = discord.Embed(
                    title="Verification Successful!",
                    description=f"You have been verified and granted access to the server!",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
                # Log to admin channel
                if admin_log_channel:
                    email = verification_data[user_id]["email"]
                    await admin_log_channel.send(f"User {interaction.user.mention} ({user_id}) verified with email {email}")
                
                # Clean up verification data
                del verification_data[user_id]
                
            except discord.Forbidden:
                embed = discord.Embed(
                    title="Error",
                    description="I don't have permission to assign roles. Please contact an admin.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            
            except Exception as e:
                embed = discord.Embed(
                    title="Error",
                    description=f"An unexpected error occurred: {str(e)}",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="Invalid Code",
                description="The verification code you entered is incorrect. Please try again.",
                color=discord.Color.red()
            )
            
            # Create a button to try again
            retry_button = discord.ui.Button(
                label="Try Again", 
                style=discord.ButtonStyle.primary, 
                custom_id="enter_code"
            )
            
            view = discord.ui.View()
            view.add_item(retry_button)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.event
async def on_interaction(interaction):
    """Handle button interactions"""
    if interaction.type == discord.InteractionType.component:
        # Handle button clicks
        custom_id = interaction.data.get('custom_id')
        if custom_id == "verify_email":
            # Show the email modal
            await interaction.response.send_modal(EmailModal(title="Email Verification"))
        
        elif custom_id == "enter_code":
            # Show the code verification modal
            await interaction.response.send_modal(CodeVerificationModal(title="Enter Verification Code"))

def send_verification_email(email, code):
    """Send a verification email using SMTP"""
    try:
        # Create message container
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Discord Server Verification Code"
        msg['From'] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
        msg['To'] = email
        
        # Create the plain-text version of the message
        text = f"Your verification code is: {code}\n\nPlease enter this code in the Discord bot to complete verification."
        
        # Create the HTML version of the message
        html = f"""
        <html>
        <body>
            <p>You've requested to join the Discord server. Your verification code is:</p>
            <div>{code}</div>
            <p>Enter this code in the Discord bot to gain access to the server.</p>
            <p>If you didn't request this verification, you can safely ignore this email.</p>
            </div>
        </body>
        </html>
        """
        
        # Attach parts to the message
        msg.attach(MIMEText(text, 'plain'))
        msg.attach(MIMEText(html, 'html'))
        
        # Connect to server and send
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
            
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

# Run the bot
if __name__ == "__main__":
    bot.run(TOKEN)