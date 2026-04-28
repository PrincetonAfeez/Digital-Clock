from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import cast

from pyclock.domain import Alarm, Time
from pyclock.exceptions import AlarmConflictError
from pyclock.paths import default_alarms_path

