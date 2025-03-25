from wagtail import blocks
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageBlock

from apps.cms.blocks import VideoBlock


class LearningContentBlock(blocks.StructBlock):
    title = blocks.CharBlock(
        required=True,
        max_length=100,
        help_text="Enter a clear, concise title for this learning nugget (max 100 characters recommended)",
    )
    thumbnail = ImageBlock(
        required=False,
        help_text="Upload a representative image that visually captures the content (recommended size: 800x450px, 16:9 ratio)",
    )
    description = blocks.RichTextBlock(
        required=False,
        help_text="Provide a comprehensive description of the learning nugget, including key takeaways and learning objectives",
    )
    video = VideoBlock(
        required=False,
        help_text="Upload or select an instructional video to complement the written content (MP4 format recommended)",
    )
    document = DocumentChooserBlock(
        required=False,
        help_text="Upload related documents such as worksheets, guides, or additional resources (PDF format recommended)",
    )

    class Meta:
        template = "a4_candy_learning_nuggets/blocks/learning_content_block.html"
        icon = "media"
        label = "Learning Nugget Content"
