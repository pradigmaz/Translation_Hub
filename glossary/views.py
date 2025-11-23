from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from projects.models import Project, ProjectMaterial
from .models import GlossaryTerm


@login_required
def glossary_list(request, project_id):
    project = get_object_or_404(Project, id=project_id, team__members=request.user)
    
    available_articles = GlossaryTerm.objects.filter(
        Q(category__content_type=project.project_type) | Q(category__content_type='general'),
        is_active=True
    ).filter(
        Q(category__scope='global') |
        Q(category__scope='user', created_by=request.user) |
        Q(category__scope='project', project=project)
    ).select_related('category', 'created_by').order_by('term')
    
    search_query = request.GET.get('q', '').strip()
    if search_query:
        available_articles = available_articles.filter(
            Q(term__icontains=search_query) | Q(definition__icontains=search_query)
        )
    
    project_materials = project.materials.select_related('created_by').order_by('order', 'title')
    if search_query:
        project_materials = project_materials.filter(
            Q(title__icontains=search_query) | Q(content__icontains=search_query)
        )
    
    categories_with_articles = {}
    for article in available_articles:
        category_name = article.category.name
        if category_name not in categories_with_articles:
            categories_with_articles[category_name] = {'category': article.category, 'articles': []}
        categories_with_articles[category_name]['articles'].append(article)
    
    return render(request, 'glossary/glossary_list.html', {
        'project': project,
        'categories_with_articles': categories_with_articles,
        'project_materials': project_materials,
        'total_articles': available_articles.count(),
        'total_materials': project_materials.count(),
    })





@login_required
def glossary_detail(request, project_id, pk):
    project = get_object_or_404(Project, id=project_id, team__members=request.user)
    article = get_object_or_404(
        GlossaryTerm.objects.select_related('category', 'created_by'),
        pk=pk,
        is_active=True
    )
    
    if not article.is_accessible_by_user(request.user):
        return redirect('glossary:glossary_list', project_id=project.id)
    
    if article.category.content_type not in [project.project_type, 'general']:
        return redirect('glossary:glossary_list', project_id=project.id)
    
    return render(request, 'glossary/glossary_detail.html', {
        'project': project,
        'article': article,
    })


@login_required
def material_detail(request, project_id, material_id):
    project = get_object_or_404(Project, id=project_id, team__members=request.user)
    material = get_object_or_404(
        ProjectMaterial.objects.select_related('created_by'),
        pk=material_id,
        project=project
    )
    
    return render(request, 'glossary/material_detail.html', {
        'project': project,
        'material': material,
    })
