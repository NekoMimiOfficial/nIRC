import ollama
from nIRC.irc import Bot, Context

@Bot.prefix_command(">")
async def ai_query_command(ctx: Context):
    """
    Fires on any message starting with '>' (e.g., >what is my status).
    """
    if ctx.arg:
        await ctx.reply("Processing...")
        model = "nekko:latest" # My private custom model, change this to something else like gemma3:latest
        prompt = ctx.arg
        current_line_buffer = ""
        response_stream = ollama.generate(model=model, prompt=prompt, stream=True)
        for chunk in response_stream:
            if 'response' in chunk:
                current_line_buffer += chunk['response']
                if '\n' in current_line_buffer:
                    lines_to_send = current_line_buffer.split('\n')
                    current_line_buffer = lines_to_send.pop()
                    for line in lines_to_send:
                        if line.strip():
                            await ctx.send(line)
        if current_line_buffer.strip():
            await ctx.send(current_line_buffer)
