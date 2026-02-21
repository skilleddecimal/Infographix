"""Organization management routes for Enterprise."""

import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session

from backend.db.base import get_db
from backend.db.models import (
    User,
    Organization,
    OrganizationMember,
    MemberRole,
    PlanType,
)
from backend.api.dependencies import CurrentUser
from backend.auth.tokens import generate_token, hash_token

router = APIRouter()


# Request/Response Models
class CreateOrganizationRequest(BaseModel):
    """Create organization request."""
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = None


class UpdateOrganizationRequest(BaseModel):
    """Update organization request."""
    name: str | None = None
    description: str | None = None
    logo_url: str | None = None
    settings: dict | None = None


class OrganizationResponse(BaseModel):
    """Organization response."""
    id: str
    name: str
    slug: str
    description: str | None
    logo_url: str | None
    owner_id: str
    member_count: int
    created_at: str


class MemberResponse(BaseModel):
    """Organization member response."""
    id: str
    user_id: str
    email: str
    name: str | None
    role: str
    joined_at: str
    invitation_pending: bool


class InviteMemberRequest(BaseModel):
    """Invite member request."""
    email: EmailStr
    role: str = "viewer"


class UpdateMemberRoleRequest(BaseModel):
    """Update member role request."""
    role: str


class InvitationResponse(BaseModel):
    """Invitation response."""
    id: str
    email: str
    role: str
    invitation_token: str | None
    invited_at: str
    accepted: bool


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:100]


def check_enterprise_access(user: User) -> None:
    """Check if user has enterprise access."""
    if user.plan != PlanType.ENTERPRISE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires an Enterprise plan",
        )


def get_user_organization_role(
    db: Session,
    user_id: str,
    org_id: str,
) -> OrganizationMember | None:
    """Get user's membership in an organization."""
    return db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user_id,
        OrganizationMember.organization_id == org_id,
    ).first()


def require_org_role(
    db: Session,
    user: User,
    org_id: str,
    required_roles: list[MemberRole],
) -> OrganizationMember:
    """Require user to have specific role in organization."""
    # Check if user is owner
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    if org.owner_id == user.id:
        # Owner has all permissions
        member = get_user_organization_role(db, user.id, org_id)
        if not member:
            # Create implicit owner membership
            member = OrganizationMember(
                organization_id=org_id,
                user_id=user.id,
                role=MemberRole.OWNER,
                invitation_accepted_at=datetime.utcnow(),
            )
            db.add(member)
            db.commit()
        return member

    member = get_user_organization_role(db, user.id, org_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization",
        )

    if member.role not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This action requires one of these roles: {[r.value for r in required_roles]}",
        )

    return member


# Organization CRUD
@router.post("", response_model=OrganizationResponse)
async def create_organization(
    request: CreateOrganizationRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Create a new organization."""
    check_enterprise_access(current_user)

    # Check if slug is taken
    existing = db.query(Organization).filter(
        Organization.slug == request.slug
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization slug already taken",
        )

    # Create organization
    org = Organization(
        name=request.name,
        slug=request.slug,
        description=request.description,
        owner_id=current_user.id,
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    # Add owner as member
    member = OrganizationMember(
        organization_id=org.id,
        user_id=current_user.id,
        role=MemberRole.OWNER,
        invitation_accepted_at=datetime.utcnow(),
    )
    db.add(member)
    db.commit()

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        logo_url=org.logo_url,
        owner_id=org.owner_id,
        member_count=1,
        created_at=org.created_at.isoformat(),
    )


@router.get("", response_model=list[OrganizationResponse])
async def list_organizations(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """List organizations the user belongs to."""
    memberships = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.invitation_accepted_at.isnot(None),
    ).all()

    org_ids = [m.organization_id for m in memberships]

    # Also include owned organizations
    owned = db.query(Organization).filter(
        Organization.owner_id == current_user.id
    ).all()
    for org in owned:
        if org.id not in org_ids:
            org_ids.append(org.id)

    organizations = db.query(Organization).filter(
        Organization.id.in_(org_ids)
    ).all()

    result = []
    for org in organizations:
        member_count = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.invitation_accepted_at.isnot(None),
        ).count()

        result.append(OrganizationResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            description=org.description,
            logo_url=org.logo_url,
            owner_id=org.owner_id,
            member_count=member_count,
            created_at=org.created_at.isoformat(),
        ))

    return result


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Get organization details."""
    require_org_role(db, current_user, org_id, list(MemberRole))

    org = db.query(Organization).filter(Organization.id == org_id).first()

    member_count = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org.id,
        OrganizationMember.invitation_accepted_at.isnot(None),
    ).count()

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        logo_url=org.logo_url,
        owner_id=org.owner_id,
        member_count=member_count,
        created_at=org.created_at.isoformat(),
    )


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    request: UpdateOrganizationRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Update organization details."""
    require_org_role(db, current_user, org_id, [MemberRole.OWNER, MemberRole.ADMIN])

    org = db.query(Organization).filter(Organization.id == org_id).first()

    if request.name is not None:
        org.name = request.name
    if request.description is not None:
        org.description = request.description
    if request.logo_url is not None:
        org.logo_url = request.logo_url
    if request.settings is not None:
        org.settings = request.settings

    db.commit()
    db.refresh(org)

    member_count = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org.id,
        OrganizationMember.invitation_accepted_at.isnot(None),
    ).count()

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        logo_url=org.logo_url,
        owner_id=org.owner_id,
        member_count=member_count,
        created_at=org.created_at.isoformat(),
    )


@router.delete("/{org_id}")
async def delete_organization(
    org_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Delete an organization (owner only)."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    if org.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can delete an organization",
        )

    db.delete(org)
    db.commit()

    return {"status": "organization_deleted"}


# Member Management
@router.get("/{org_id}/members", response_model=list[MemberResponse])
async def list_members(
    org_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """List organization members."""
    require_org_role(db, current_user, org_id, list(MemberRole))

    members = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
    ).all()

    result = []
    for member in members:
        user = db.query(User).filter(User.id == member.user_id).first()
        result.append(MemberResponse(
            id=member.id,
            user_id=member.user_id,
            email=user.email if user else "",
            name=user.name if user else None,
            role=member.role.value,
            joined_at=member.invitation_accepted_at.isoformat() if member.invitation_accepted_at else member.created_at.isoformat(),
            invitation_pending=member.invitation_accepted_at is None,
        ))

    return result


@router.post("/{org_id}/members/invite", response_model=InvitationResponse)
async def invite_member(
    org_id: str,
    request: InviteMemberRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Invite a user to the organization."""
    require_org_role(db, current_user, org_id, [MemberRole.OWNER, MemberRole.ADMIN])

    # Validate role
    try:
        role = MemberRole(request.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {[r.value for r in MemberRole]}",
        )

    # Cannot invite as owner
    if role == MemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot invite as owner. Transfer ownership instead.",
        )

    # Check if user exists
    user = db.query(User).filter(User.email == request.email).first()

    # Check if already a member
    if user:
        existing = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user.id,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member or has pending invitation",
            )

    # Generate invitation token
    token = generate_token()

    # Create member with pending invitation
    member = OrganizationMember(
        organization_id=org_id,
        user_id=user.id if user else None,
        role=role,
        invited_by_id=current_user.id,
        invitation_token=hash_token(token),
    )

    # If user doesn't exist, we'll create a placeholder
    # In production, you'd send an email invitation
    if not user:
        # For now, reject invitations to non-existing users
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found. They must register first.",
        )

    db.add(member)
    db.commit()
    db.refresh(member)

    # TODO: Send invitation email with token
    print(f"[DEV] Invitation token for {request.email}: {token}")

    return InvitationResponse(
        id=member.id,
        email=request.email,
        role=member.role.value,
        invitation_token=token,  # Only shown once
        invited_at=member.created_at.isoformat(),
        accepted=False,
    )


@router.post("/invitations/accept")
async def accept_invitation(
    token: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Accept an organization invitation."""
    token_hash = hash_token(token)

    member = db.query(OrganizationMember).filter(
        OrganizationMember.invitation_token == token_hash,
        OrganizationMember.user_id == current_user.id,
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invitation token",
        )

    if member.invitation_accepted_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation already accepted",
        )

    member.invitation_accepted_at = datetime.utcnow()
    member.invitation_token = None
    db.commit()

    org = db.query(Organization).filter(
        Organization.id == member.organization_id
    ).first()

    return {
        "status": "invitation_accepted",
        "organization": {
            "id": org.id,
            "name": org.name,
        },
    }


@router.patch("/{org_id}/members/{member_id}", response_model=MemberResponse)
async def update_member_role(
    org_id: str,
    member_id: str,
    request: UpdateMemberRoleRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Update a member's role."""
    require_org_role(db, current_user, org_id, [MemberRole.OWNER, MemberRole.ADMIN])

    member = db.query(OrganizationMember).filter(
        OrganizationMember.id == member_id,
        OrganizationMember.organization_id == org_id,
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    # Validate role
    try:
        role = MemberRole(request.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {[r.value for r in MemberRole]}",
        )

    # Cannot change owner role
    if member.role == MemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change owner's role. Transfer ownership instead.",
        )

    # Cannot promote to owner
    if role == MemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot promote to owner. Transfer ownership instead.",
        )

    member.role = role
    db.commit()
    db.refresh(member)

    user = db.query(User).filter(User.id == member.user_id).first()

    return MemberResponse(
        id=member.id,
        user_id=member.user_id,
        email=user.email if user else "",
        name=user.name if user else None,
        role=member.role.value,
        joined_at=member.invitation_accepted_at.isoformat() if member.invitation_accepted_at else member.created_at.isoformat(),
        invitation_pending=member.invitation_accepted_at is None,
    )


@router.delete("/{org_id}/members/{member_id}")
async def remove_member(
    org_id: str,
    member_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Remove a member from the organization."""
    require_org_role(db, current_user, org_id, [MemberRole.OWNER, MemberRole.ADMIN])

    member = db.query(OrganizationMember).filter(
        OrganizationMember.id == member_id,
        OrganizationMember.organization_id == org_id,
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    # Cannot remove owner
    if member.role == MemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the owner. Transfer ownership first.",
        )

    db.delete(member)
    db.commit()

    return {"status": "member_removed"}


@router.post("/{org_id}/leave")
async def leave_organization(
    org_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Leave an organization."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Owner cannot leave
    if org.owner_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Owner cannot leave. Transfer ownership or delete the organization.",
        )

    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == current_user.id,
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not a member of this organization",
        )

    db.delete(member)
    db.commit()

    return {"status": "left_organization"}


@router.post("/{org_id}/transfer-ownership")
async def transfer_ownership(
    org_id: str,
    new_owner_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Transfer organization ownership to another member."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    if org.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can transfer ownership",
        )

    # Check new owner is a member
    new_owner_member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == new_owner_id,
        OrganizationMember.invitation_accepted_at.isnot(None),
    ).first()

    if not new_owner_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New owner must be an active member of the organization",
        )

    # Update ownership
    org.owner_id = new_owner_id

    # Update roles
    old_owner_member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == current_user.id,
    ).first()

    if old_owner_member:
        old_owner_member.role = MemberRole.ADMIN

    new_owner_member.role = MemberRole.OWNER

    db.commit()

    return {"status": "ownership_transferred"}
