# SKILLBRIDGE AI - FULL PROJECT BRIEF

> Consolidated rebuild specification

# SKILLBRIDGE AI

# COMPLETE PROJECT REBUILD — MASTER DEVELOPMENT PROMPT
Act as a senior software architect, full-stack Python developer, AI engineer, data scientist, database engineer, DevOps engineer and professional UI/UX designer.

Your assignment is to completely rebuild my existing SkillBridge AI project.

The final result must be a complete, functional, secure, data-driven, AI-powered career development platform that can be deployed online and used by students.

This is a full project rebuild, not a small update.

Do not create a prototype, static mockup or demonstration.

Every major feature must work with real user input, real data, persistent storage and genuine AI responses.

==================================================

1. PROJECT VISION
==================================================
SkillBridge AI is a universal AI-powered career development platform.

It helps students move from:

"I want to pursue this career."

To:

"These are the skills I need, these are my current strengths, these are my skill gaps, this is what I should learn, these are the projects I should build and these are the opportunities I can pursue."

The platform must support ALL occupations across ALL industries.

It must not be restricted to technology, engineering, healthcare, animation, business or any other individual sector.

Examples include:

- Software Developer
- AI Engineer
- Mechanical Engineer
- Electrical Engineer
- Aerospace Engineer
- Doctor
- Nurse
- Pharmacist
- Lawyer
- Accountant
- Teacher
- Architect
- Animator
- Video Game Designer
- Graphic Designer
- Film Director
- Music Producer
- Electrician
- Plumber
- Carpenter
- Automotive Technician
- Chef
- Entrepreneur
- Environmental Scientist
- Research Scientist
- Financial Analyst
- Marketing Manager
The application must also support occupations entered manually when they are not available in the occupational database.

Desktop:

- Python 3.11+
- PyQt6
Backend:

- Python
- FastAPI
- REST API
- HTTPS
Database:

- PostgreSQL for production
- SQLite for local development where appropriate
- SQLAlchemy
- Alembic
AI:

- Google Gemini API
- Gemini vision capabilities where supported
Occupational data:

- Official O*NET database
- CSV import and validation
- O*NET Web Services API where appropriate
Other:

- Matplotlib
- Pillow
- Pydantic
- HTTPX
- python-dotenv
- Pytest
Do not use:

- Streamlit
- Flask
- Django
- React
- JavaScript
- HTML-based desktop interfaces
The desktop application must use native PyQt6.

Before changing anything:

1. Inspect the entire existing repository.
2. Identify existing functionality and dependencies.
3. Check the current branch and working tree.
4. Identify broken and incomplete features.
5. Create a backup branch named skillbridge-backup.
6. Create a development branch named skillbridge-rebuild.
7. Preserve useful assets and documentation.
I want the new implementation to eventually replace the existing project on the main GitHub branch.

IMPORTANT:

- Never force-push.
- Never delete the backup branch.
- Never expose API keys.
- Never overwrite unrelated repositories.
- Never delete user data without confirmation.
- Never commit .env files containing real credentials.
- Never merge the replacement into main without my approval.
Build and test on the development branch first.

Implement the following architecture:

Student's PyQt6 desktop application
|
| HTTPS
|
v
FastAPI backend
|
---------------------
|         |         |
v         v         v
Gemini   PostgreSQL   O*NET
|
v
Personalised AI guidance

The desktop application communicates with the backend.

The backend manages:

- Authentication
- User profiles
- Career information
- O*NET data
- AI requests
- Skill assessments
- Learning roadmaps
- Portfolio evaluations
- Project generation
- Opportunity discovery
- Progress tracking
Never expose backend credentials to desktop clients.

Students must not need their own Gemini API keys.

Implement a secure server-side Gemini integration.

Requirements:

1. Configure GEMINI_API_KEY on the backend.
2. Store the key in a secure environment variable or secret manager.
3. Never embed the key in the desktop application.
4. Never return the key through API responses.
5. Create one central Gemini service.
6. Connect every AI feature to this service.
7. Validate AI responses.
8. Handle timeouts, errors and outages.
9. Implement request limits and usage tracking.
10. Do not generate fake responses when Gemini is unavailable.
Gemini must power:

- Career Explorer
- Career Reality Check
- Skill Gap Analyzer
- Learning Roadmap
- Portfolio Reviewer
- Project Generator
If the Gemini service is unavailable, display an accurate error message.

Non-AI functionality should continue working where possible.

THIS IS A CORE REQUIREMENT OF SKILLBRIDGE AI.

Use the official O*NET occupational database as the primary structured source for US occupational information.

Official download:

[https://www.onetcenter.org/database.html](https://www.onetcenter.org/database.html)

Official web services:

[https://services.onetcenter.org/](https://services.onetcenter.org/)

Use the complete available O*NET database version supplied by the user.

Do not manually restrict the database to selected industries.

The application must support every occupation represented in the imported dataset.

A. DATA TO IMPORT

Prioritize all relevant available O*NET datasets, including:

- Occupation Data
- Alternate Titles
- Skills
- Knowledge
- Abilities
- Education, Training and Experience
- Work Activities
- Detailed Work Activities
- Tasks
- Work Styles
- Work Context
- Related Occupations
- Technology Skills
- Interests
- Work Values
Import the relevant available records rather than limiting the system to only the first few CSV files.

B. DATABASE REQUIREMENTS

Preserve:

- O*NET-SOC occupation codes
- Descriptor IDs
- Element IDs
- Rating values
- Rating scales
- Source metadata
- Database version
Build relational database tables connecting:

- Occupations
- Alternate job titles
- Skills
- Knowledge
- Abilities
- Tasks
- Work activities
- Education requirements
- Related occupations
- Technology skills
Avoid duplicate records.

C. DATA IMPORT SYSTEM

Create an O*NET import interface.

Users with administrator permissions should be able to:

- Select the downloaded O*NET archive.
- Validate the archive.
- Import the records.
- View import progress.
- View successful imports.
- View failed records.
- Review database version.
- Update the database later.
Support repeatable imports without creating duplicate records.

If the dataset has not been downloaded, display instructions explaining which official files are required.

Do not pretend the dataset has been imported when it has not.

D. CAREER SEARCH

Allow users to search using:

- Job title
- Alternative job title
- Occupation description
- Occupation code
- Industry or category where available
Support career comparisons.

E. UNIVERSAL CAREER SUPPORT

O*NET must provide the structured occupational information, but the application must also allow manually entered careers outside the database.

For careers not found in O*NET:

- Let users enter a custom occupation.
- Use Gemini to provide clearly labeled general career guidance.
- Identify which information is not verified.
- Never fabricate official O*NET records.
F. ATTRIBUTION

Display the O*NET source, database version and applicable attribution.

Follow O*NET data terms and licensing requirements.

Build a complete account system.

Features:

- Create account
- Login
- Logout
- Password hashing
- Secure authentication
- Password recovery
- Profile editing
- Account deletion
Profile information:

- Display name
- Age range
- Education level
- Country
- State or region
- Career interests
- Current skills
- Previous experience
- Learning preferences
- Weekly availability
- Career goals
Allow multiple career interests.

Do not assume every student follows the same education pathway.

Create a personalized dashboard.

Display:

- Welcome message
- Career interests
- Current learning roadmap
- Skills being developed
- Completed activities
- Portfolio projects
- Recent AI feedback
- Saved opportunities
- Weekly activity
- Overall progress
All dashboard information must come from actual saved database records.

Never fabricate achievements or progress.

Build a searchable career discovery system.

Students can:

- Search all imported O*NET occupations.
- Search alternative job titles.
- Enter custom careers.
- Browse occupational categories.
- Compare occupations.
- Save careers.
- Explore related occupations.
Display:

- Occupation description
- Required skills
- Knowledge areas
- Abilities
- Work activities
- Typical tasks
- Education information where available
- Technology skills
- Related occupations
Use O*NET as the factual foundation.

Use Gemini to explain occupational information in understandable language.

Clearly distinguish official data from AI-generated explanations.

Build an AI-powered career evaluation feature.

Explain:

- What professionals actually do
- Required foundational knowledge
- Important technical and practical skills
- Common challenges
- Education pathways
- Training requirements
- Practical preparation
- Related careers
Do not guarantee salaries, employment or admission.

Adapt the explanation to the selected occupation and the student's education level.

Compare:

Student's reported current skills

AGAINST

The selected occupation's actual O*NET requirements.

Generate:

- Skills the student reports having
- Skills requiring development
- Important foundational knowledge
- Learning priorities
- Practical skill demonstrations
- Suggested projects
Use actual O*NET occupational information.

Use Gemini to explain and personalize the analysis.

Do not claim to have independently verified a student's abilities.

Do not use the same generic skill checklist for every occupation.

Generate personalized learning roadmaps.

Each roadmap must adapt to the selected occupation.

Include:

- Learning stages
- Skills to develop
- Prerequisites
- Learning objectives
- Suggested resources
- Practical exercises
- Projects
- Estimated time ranges
- Completion criteria
Support different pathways:

- University education
- Community college
- Vocational education
- Apprenticeships
- Certifications
- Direct work experience
- Other relevant pathways
For example:

An aspiring electrician should receive an appropriate trade training and apprenticeship pathway.

An aspiring doctor should receive an appropriate academic and medical education pathway.

An aspiring animator should receive an art, design and portfolio development pathway.

An aspiring accountant should receive an accounting education and professional qualification pathway.

Students can:

- Mark activities complete.
- Add notes.
- Edit activities.
- Reorder activities.
- Pause activities.
- Save progress.
- Request roadmap updates.
Never automatically mark activities complete.

Ask before replacing an existing roadmap.

Allow students to upload:

- Project images
- Screenshots
- Design work
- Supported documents
- Project descriptions
Use Gemini vision where supported.

Evaluate:

- Technical execution
- Creativity
- Problem-solving
- Career relevance
- Demonstrated skills
- Presentation
- Areas for improvement
Return actionable feedback.

Save the project and evaluation.

Do not claim to analyze an image unless it was actually processed.

Generate projects based on:

- Selected occupation
- Student experience
- Current skills
- Skills they want to develop
Each project should contain:

- Title
- Description
- Difficulty
- Required materials
- Software where applicable
- Skills developed
- Learning objectives
- Development stages
- Expected outcome
- Portfolio presentation suggestions
Make project suggestions appropriate to the student's education level and resources.

Allow students to save projects and track progress.

Create a dedicated module for:

COLLEGES AND UNIVERSITIES:

- Relevant programs
- Majors
- Admission requirements
- Tuition information
- Application deadlines
- Official application links
EVENTS:

- Hackathons
- Competitions
- Workshops
- Conferences
- Career fairs
- Student events
INTERNSHIPS:

- High school internships
- Student internships
- Entry-level programs
- Industry-specific internships
SUMMER PROGRAMS:

- University programs
- Pre-college programs
- Vocational programs
- Research programs
- Creative programs
Use real external information sources.

Gemini must not be treated as a live source of deadlines, admissions requirements or event availability.

Each result should include:

- Name
- Description
- Location
- Official URL
- Date or deadline
- Eligibility
- Retrieval date
- Verification status
Never invent opportunities or deadlines.

Allow students to save opportunities and track applications.

If live search is unavailable, clearly communicate the limitation.

Use Matplotlib to display actual database information.

Track:

- Skills developed
- Completed learning activities
- Projects completed
- Portfolio growth
- Roadmap completion
- Weekly activity
Never generate fake analytics.

Build a premium native PyQt6 interface.

Design:

- Dark navy background
- Electric blue and purple accents
- Professional typography
- Modern sidebar
- Rounded cards
- Clean layouts
- Consistent icons
- Subtle borders
- Modern charts
- Loading indicators
- Clear notifications
Sidebar:

1. Dashboard
2. My Profile
3. Career Explorer
4. Career Reality Check
5. Skill Gap Analyzer
6. Learning Roadmap
7. Portfolio Reviewer
8. Project Generator
9. Opportunities & Colleges
10. Progress Analytics
11. Settings
Every navigation item must work.

Every button must perform its advertised operation.

Do not create decorative or nonfunctional controls.

Persist:

- User accounts
- Profiles
- Career interests
- O*NET occupations
- O*NET descriptors
- Skill assessments
- Roadmaps
- Learning activities
- Portfolio projects
- AI evaluations
- Project ideas
- Saved opportunities
- Progress records
Implement:

- Secure password hashing
- Authentication
- Authorization
- User data isolation
- Input validation
- HTTPS
- Rate limiting
- Secure file upload validation
- File size limits
- Private file storage
- Database migrations
- Backup guidance
- Error handling
One user must never access another user's private records.

Prepare for continuous cloud hosting.

Preferred initial hosting: Railway.

Implement:

- Dockerfile
- Docker Compose for local development
- Railway configuration
- PostgreSQL production connection
- Database migrations
- Environment variable documentation
- Health endpoint
- Production startup command
Create:

GET /health

The endpoint must accurately report backend and required dependency health.

The desktop application must connect to a configurable backend URL.

Students must not need Gemini API credentials.

Do not claim successful deployment without testing the actual deployed service.

Keep the desktop application responsive.

Use QThread or appropriate workers for:

- Gemini requests
- File processing
- Portfolio review
- Database operations
- Opportunity searches
Provide:

- Loading indicators
- Progress updates
- Error messages
- Retry options
Create a maintainable project structure similar to:

SkillBridgeAI/
desktop/
main.py
application.py
ui/
services/
workers/
assets/

```
backend/
    main.py
    api/
    services/
    database/
    models/
    schemas/
    security/

data/
    onet/
    imports/

tests/

Dockerfile
docker-compose.yml
requirements.txt
.env.example
.gitignore
README.md
```
Improve this structure if necessary.

Create automated tests for:

- Registration
- Login
- Profile persistence
- O*NET dataset imports
- Occupation search
- Alternative job title search
- Career comparison
- Custom occupations
- Skill gap analysis
- Gemini connectivity
- Roadmap generation
- Roadmap persistence
- Portfolio uploads
- Portfolio evaluation
- Project generation
- Opportunity discovery
- User data isolation
- Authentication failures
- Backend outages
- Database persistence
Test occupations across at least ten different industries.

Do not test only technology careers.

Work in stages.

STAGE 1:
Inspect repository, create backup branch and development branch.

STAGE 2:
Build backend, database and authentication.

STAGE 3:
Build PyQt6 interface.

STAGE 4:
Integrate the complete O*NET database.

STAGE 5:
Integrate Gemini securely.

STAGE 6:
Build universal Career Explorer and Skill Gap Analyzer.

STAGE 7:
Build Learning Roadmap and Project Generator.

STAGE 8:
Build Portfolio Reviewer and Opportunity Discovery.

STAGE 9:
Build Analytics.

STAGE 10:
Test, fix bugs and prepare cloud deployment.

Do not skip testing.

Do not stop after generating source files.

Run the application.

Test actual user workflows.

Fix discovered errors.

The project is complete only when:

1. The desktop application launches.
2. Registration works.
3. Login works.
4. User profiles persist.
5. The O*NET dataset imports successfully.
6. Career searches return actual occupational records.
7. Alternative job titles work.
8. Custom occupations are supported.
9. Career comparisons work.
10. Skill gap analysis uses actual occupational data.
11. Gemini returns genuine responses.
12. Learning roadmaps can be saved.
13. Portfolio images can be uploaded and reviewed.
14. Projects can be generated and tracked.
15. User data is isolated.
16. Backend deployment is prepared.
17. Desktop-to-backend communication works.
18. Automated tests pass for implemented functionality.
If any requirement remains incomplete, report it honestly.

Deliver:

- Complete Windows desktop application
- Secure FastAPI backend
- Gemini integration
- Full O*NET dataset integration
- Persistent database
- User authentication
- Universal career exploration
- Career Reality Check
- Skill Gap Analyzer
- Adaptive Learning Roadmap
- Portfolio Reviewer
- Project Generator
- Opportunity and College Discovery
- Progress Analytics
- Automated tests
- Deployment configuration
- Documentation
The final product must support students interested in ANY occupation across ANY industry.

It must not be a technology-only or university-only career platform.

First inspect the repository. Build the replacement on the development branch. Test it thoroughly.

Do not merge into the main branch until I have reviewed the implementation and confirmed the replacement.

==================================================
26. SKILLBRIDGE AI — OWN AI MODEL AND COMMUNITY KNOWLEDGE SYSTEM
==================================================
Build the foundation for SkillBridge AI to eventually have its own independently developed AI system.

The long-term goal is to reduce dependence on external AI providers such as Gemini and develop a proprietary SkillBridge AI model that improves using high-quality, permission-based contributions from its community.

This must be designed as a long-term AI development project, not a fake AI feature.

## A. OWN AI ARCHITECTURE
Create a modular AI architecture that supports multiple providers:
- Gemini as the initial AI provider.
- A future proprietary SkillBridge AI model.
- Other AI models when appropriate.
Create a centralized AI service layer so the application can switch between providers without rebuilding every feature.

## B. COMMUNITY CONTRIBUTIONS
Allow students to voluntarily contribute useful educational information:
- Learning resources.
- Career research.
- Project descriptions and development experiences.
- Skill explanations.
- Career preparation guides.
- Learning roadmaps.
- Portfolio improvement examples.
- Verified corrections to career information.
- Training exercises and educational questions.

Every contribution must have:
- Contributor ownership information.
- Submission date.
- Category.
- Source information where applicable.
- Review status.
- Quality rating.
- Permission and consent status.
Contributions must not automatically become AI training data.

## C. USER CONSENT AND PRIVACY
1. Participation must be optional.
2. Users must understand what they are sharing.
3. Do not use private profiles, passwords, personal messages, school records, uploaded personal documents, or private portfolio information for model training.
4. Never collect sensitive personal information for training.
5. Remove identifying information before eligible data enters the training pipeline.
6. Keep private user data separate from community contributions.
7. Allow users to withdraw future training permission.
8. Do not assume that using SkillBridge AI means agreeing to AI training.
9. Respect copyright and ownership of submitted materials.
10. Do not train on information without appropriate permission.

## D. COMMUNITY KNOWLEDGE DATABASE
Create a separate database for approved community knowledge:
- Career knowledge.
- Learning resources.
- Skill explanations.
- Project examples.
- Educational questions.
- Reviewed answers.
- Source references.
- Quality scores.
- Review history.
Build moderation and review workflows.
Unverified submissions must never be presented as verified facts.

## E. AI TRAINING PIPELINE
Create an architecture that eventually supports:
1. Data collection with consent.
2. Data validation.
3. Personal information removal.
4. Duplicate detection.
5. Copyright and permission checks.
6. Human quality review.
7. Dataset versioning.
8. Training and validation splits.
9. Model evaluation.
10. Model versioning.
11. Controlled deployment.
12. Rollback to a previous model.
Do not automatically train a model when someone submits information.
Training must happen through controlled, reviewed releases.

## F. RETRIEVAL-AUGMENTED GENERATION
Before attempting to train a large language model from scratch, implement knowledge retrieval using:
- Embeddings.
- Vector search.
- Approved community contributions.
- Official O*NET occupational data.
- Trusted educational resources.
Retrieve relevant information before generating an answer.
Show sources when available.
Clearly distinguish retrieved information from AI-generated explanations.

## G. FUTURE PROPRIETARY MODEL
Prepare the system to support a separately trained SkillBridge AI model.
The future model should specialize in:
- Career exploration.
- Occupational skill analysis.
- Learning recommendations.
- Project guidance.
- Portfolio feedback.
- Career pathway explanations.
Support model evaluation before deployment.
Do not replace Gemini with an untested model.
Do not claim SkillBridge AI has its own trained model until an actual model has been trained, evaluated, and deployed.

## H. ADMINISTRATOR CONTROL PANEL
Create an administrator interface showing:
- Total community contributions.
- Pending submissions.
- Approved submissions.
- Rejected submissions.
- Training-eligible records.
- Consent statistics.
- Dataset versions.
- Training history.
- Model versions.
- Evaluation results.
Restrict administrator operations using role-based access control.

## I. IMPORTANT DEVELOPMENT RULES
Build in stages:
1. Implement the community contribution database.
2. Implement consent management, moderation, and retrieval.
3. Prepare data-processing and model-training infrastructure.
Do not attempt to train a large language model from scratch using a small student dataset.
Do not use private student information as training material.
Do not fabricate training progress, model accuracy, or AI capabilities.
The ultimate objective is to develop a trustworthy proprietary SkillBridge AI system that improves through permission-based community knowledge and carefully evaluated model development.
