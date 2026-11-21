"""Reference data about the official O*NET database distribution."""

ONET_URL = "https://www.onetcenter.org/database.html"
ONET_LICENSE = "https://creativecommons.org/licenses/by/4.0/"
ONET_CREDIT = "O*NET® Database, U.S. Department of Labor, Employment and Training Administration"
ATTRIBUTION_NOTICE = "Imported and reformatted by SkillBridge AI; not endorsed by USDOL/ETA."

# Descriptor categories whose "IM" (importance) ratings describe skill requirements.
RATED_SKILL_CATEGORIES = ("Skills", "Essential Skills", "Transferable Skills", "Knowledge", "Abilities")

MAX_UNCOMPRESSED_BYTES = 750 * 1024 * 1024
MAX_MEMBERS = 500

# Normalised file stem (lower-case, alphanumerics only) -> descriptor category stored for its rows.
FILE_CATEGORIES = {
    "skills": "Skills",
    "essentialskills": "Essential Skills",
    "transferableskills": "Transferable Skills",
    "knowledge": "Knowledge",
    "abilities": "Abilities",
    "educationtrainingandexperience": "Education",
    "education": "Education",
    "trainingandexperience": "Training and Experience",
    "jobzones": "Job Zones",
    "workactivities": "Work Activities",
    "detailedworkactivities": "Detailed Work Activities",
    "taskstodwas": "Detailed Work Activities",
    "tasks": "Tasks",
    "taskstatements": "Tasks",
    "taskratings": "Task Ratings",
    "emergingtasks": "Emerging Tasks",
    "workstyles": "Work Styles",
    "workcontext": "Work Context",
    "technologyskills": "Technology Skills",
    "softwareskills": "Technology Skills",
    "interests": "Interests",
    "careerinteresttypes": "Interests",
    "specificinterestareas": "Specific Interest Areas",
    "workvalues": "Work Values",
}
TITLE_FILES = frozenset({"alternatetitles", "jobtitles", "sampleofreportedtitles"})
OCCUPATION_FILE = "occupationdata"
RELATED_FILE = "relatedoccupations"
README_FILE = "readme"

TITLE_COLUMNS = ("Job Title", "Alternate Title", "Reported Job Title")
DESCRIPTOR_NAME_COLUMNS = (
    "Workplace Example", "Example", "Technology", "DWA Element Name",
    "DWA Title", "Element Name", "Task", "Job Zone", "Commodity Title",
)
DESCRIPTOR_ELEMENT_COLUMNS = (
    "DWA Element ID", "DWA ID", "Element ID", "Task ID", "Commodity Code", "Original Task ID",
)
