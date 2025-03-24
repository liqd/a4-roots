import pytest
from django.urls import reverse
from wagtail.models import Page
from apps.learning_nuggets.models import LearningCenterPage, LearningCategory, LearningNuggetPage

@pytest.mark.django_db
def test_learning_center_page_is_single_instance():
      main_page = LearningCenterPage.objects.create
      
@pytest.mark.django_db
def test_learning_category_slug():
    category = LearningCategory.objects.create(name="Test Category")
    assert category.slug == "test-category", "Slug should be auto-generated from name"

@pytest.mark.django_db
def test_learning_nugget_has_category(client):
        root_page = Page.get_first_root_node()
        category = LearningCategory.objects.create(name="Participants", slug="participants")
        nugget = LearningNuggetPage(
            title="Registration",
            slug="registration",
            category=category,
        )
        root_page.add_child(instance=nugget)
        nugget.save()
        
        # Ensure the category is assigned correctly
        assert nugget.category is not None
        assert nugget.category.slug == "participants"

        # Ensure URL resolution works
        response = client.get(reverse("nugget", kwargs={"category_slug": "participants", "nugget_slug": "registration"}))
        assert response.status_code == 200 