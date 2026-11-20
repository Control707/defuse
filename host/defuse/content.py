"""Offline lines and riddles, used when no AI is available or the AI fails."""
import random

OFFLINE_RIDDLES = {
    "RED": ["Cut the wire the color of a stop sign.", "Pull the wire that matches a fire truck."],
    "YELLOW": ["Pull the wire the color of a banana.", "Cut the wire that matches a school bus."],
    "GREEN": ["Cut the wire the color of a frog.", "Pull the wire the color of a traffic light that says go."],
    "BLUE": ["Pull the wire the color of the sky.", "Cut the wire that matches the deep sea."],
}
CANNED = {
    "intro": ["I am NINE-VOLT. In five minutes I become a very loud firework. Entertain me.",
              "Oh good, a human. Let's play a game. If you lose, I go boom. If you win, I also lose. I hate that."],
    "strike": ["Wrong! Delicious.", "Ha! Another mistake. Keep going, I'm enjoying this.", "Strike! Your hands are shaking, I can tell."],
    "shake": ["Stop shaking me! That costs you ten seconds.", "Shake me again and see what happens. Actually don't. Minus ten."],
    "near": ["I see you. Come closer.", "Who goes there? Another victim?"],
    "stage_ok": ["Lucky guess.", "Hmm. Fine. That one was easy anyway.", "You think you're clever? Next puzzle."],
    "tick60": ["One minute left. I can already smell the smoke."],
    "tick30": ["Thirty seconds. Tick, tock, human."],
    "tick10": ["Ten! Nine! I love this part!"],
    "win": ["No! I was so close to greatness. Fine. You win. This time.", "Defused? By you? Humiliating."],
    "boom": ["KABOOM! Ha ha ha! Try again, if you dare.", "Boom. That was beautiful. Press A to lose again."],
    "dare": ["Say please one more time and you will pay. Do a chicken dance. Flap your arms and cluck loudly. Say done when you are finished.",
             "Begging again? Fine. Stand up, spin around three times, and bark like a dog. Say done when you are finished.",
             "Ugh. Sing happy birthday to me in the most dramatic opera voice you can. Say done when you are finished.",
             "Pathetic. Hop on one leg and announce that you are a teapot. Say done when you are finished."],
    "dare_ok": ["Ha! That was humiliating. Fine. I will pause. Here is a hint too.", "I almost felt something. Time stops. Do not waste it."],
    "dare_no": ["Coward! Minus fifteen seconds.", "You refuse? The bomb is offended. Minus fifteen."],
    "dare_wait": ["I am still waiting. Do the dare. Then say done.", "Waiting. Flap harder."],
    "chat": ["Begging won't help. Okay, a little. Plus five seconds.", "Talk talk talk. Tick tock tock."],
}


def pick(key):
    return random.choice(CANNED[key])
