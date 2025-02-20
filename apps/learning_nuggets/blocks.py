from wagtail import blocks
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock

from apps.cms.blocks import VideoBlock


class LearningContentBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True, help_text="Title of the nugget")
    description = blocks.RichTextBlock(required=False, help_text="Detailed description")
    video = VideoBlock(required=False, help_text="Upload or select a video")
    document = DocumentChooserBlock(
        required=False, help_text="Upload related documents"
    )
    thumbnail = ImageChooserBlock(required=False, help_text="Thumbnail for the nugget")

    class Meta:
        template = "blocks/learn_center/learning_content_block.html"
        icon = "media"
        label = "Learning Nugget Content"
