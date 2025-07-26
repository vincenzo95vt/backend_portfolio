from .education import protected_router as education_router
from .projects import protected_router as project_router
from .about import protected_router as about_router
from .experience import protected_router as experience_router
from .main import router as core_router
__all__ = ['education_router', 'project_router', 'about_router', 'experience_router', 'core_router']