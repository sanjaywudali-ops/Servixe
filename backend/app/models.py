"""Import every model so Alembic/metadata sees all tables."""
from app.modules.identity.models import *  # noqa
from app.modules.audit.models import *  # noqa
from app.modules.families.models import *  # noqa
from app.modules.catalogue.models import *  # noqa
from app.modules.providers.models import *  # noqa
from app.modules.requests.models import *  # noqa
from app.modules.approvals.models import *  # noqa
from app.modules.assignments.models import *  # noqa
from app.modules.evidence.models import *  # noqa
from app.modules.incidents.models import *  # noqa
from app.modules.billing.models import *  # noqa
from app.modules.notifications.models import *  # noqa
from app.modules.enquiries.models import *  # noqa
