from .education import router as education_router
from .projects import router as project_router
from .about import router as about_router
from .experience import router as experience_router
from .main import router as core_router
__all__ = ['education_router', 'project_router', 'about_router', 'experience_router', 'core_router']