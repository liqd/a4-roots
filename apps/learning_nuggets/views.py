# apps/learning_nuggets/views.py
from django.views.generic import DetailView, ListView
from wagtail.models import Page
from django.shortcuts import get_object_or_404
from .models import LearningCategory, LearningNuggetPage

class LearningCenterView(ListView):
    """Main learning center page that shows all categories"""
    template_name = 'learning_center_index.html'
    context_object_name = 'categories'
    model = LearningCategory
    
    def get_template_names(self):
        if self.request.is_ajax:
            return ['ajax/category_list.html']
        return [self.template_name]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add the main learning center page
        if not self.request.is_ajax:
            page = get_object_or_404(Page, slug='learning-center')
            context['page'] = page.specific
        return context

class LearningCategoryView(DetailView):
    """View for a specific category, showing all nuggets in that category"""
    template_name = 'learning_categories_page.html'
    context_object_name = 'category'

    def get_template_names(self):
        if self.request.is_ajax:
            return ['ajax/nugget_detail.html']
        return [self.template_name]
    
    def get_object(self):
        # Get the category based on the slug from the URL
        return get_object_or_404(LearningCategory, slug=self.kwargs['category_slug'])

class LearningNuggetView(DetailView):
    """View for a specific learning nugget"""
    template_name = 'learning_nugget_page.html'
    context_object_name = 'nugget'
    
    def get_template_names(self):
        if self.request.is_ajax:
            return ['ajax/nugget_detail.html']
        return [self.template_name]
    
    def get_object(self):
        # Get the nugget based on the slug, ensuring it belongs to the correct category
        category = get_object_or_404(LearningCategory, slug=self.kwargs['category_slug'])
        return get_object_or_404(LearningNuggetPage, slug=self.kwargs['nugget_slug'], category=category)