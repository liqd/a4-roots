from django import template

register = template.Library()


@register.simple_tag
def file_type(media_file):
    if media_file.endswith(".mp4"):
        return "video/mp4"
    elif media_file.endswith(".webm"):
        return "video/webm"
    elif media_file.endswith(".mp3"):
        return "audio/mp3"
    elif media_file.endswith(".wav"):
        return "audio/wav"
    else:
        return "type invalid"
