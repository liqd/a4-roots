from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageBlock

from apps.cms.blocks import VideoBlock


class LearningContentBlock(blocks.StructBlock):
    title = blocks.CharBlock(
        required=True,
        max_length=100,
        help_text=_(
            "Enter a clear, concise title for this learning nugget "
            "(max 100 characters recommended)"
        ),
    )
    thumbnail = ImageBlock(
        required=False,
        help_text=_(
            "Upload a representative image that visually captures the content "
            "(recommended size: 600x400px, 3:2 ratio)"
        ),
    )
    description = blocks.RichTextBlock(
        required=False,
        help_text=_(
            "Provide a comprehensive description of the learning nugget, "
            "including key takeaways and learning objectives"
        ),
    )
    video = VideoBlock(
        required=False,
        help_text=_(
            "Upload or select an instructional video to complement the written content "
            "(MP4 format recommended)"
        ),
    )
    document = DocumentChooserBlock(
        required=False,
        help_text=_(
            "Upload related documents such as worksheets, guides, "
            "or additional resources (PDF format recommended)"
        ),
    )

    class Meta:
        template = "a4_candy_learning_nuggets/blocks/learning_content_block.html"
        icon = "media"
        label = "Learning Nugget Content"
