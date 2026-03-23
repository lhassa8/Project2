"""API routes for template library."""

from fastapi import APIRouter, HTTPException

from ..services.templates import get_template, list_templates

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("")
def get_templates() -> list[dict]:
    """List all available agent scenario templates."""
    return list_templates()


@router.get("/{template_id}")
def get_template_detail(template_id: str) -> dict:
    """Get full template definition including agent config and run context."""
    tmpl = get_template(template_id)
    if tmpl is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl
