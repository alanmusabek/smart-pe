# Smart PE — cloud demonstration

This branch contains a curated deployment snapshot of the React application and FastAPI backend. It uses a separate database with fictional students. Local credentials, student exports, training records and reports are excluded.

Follow [the free deployment and presentation guide](docs/free-demo.md) to create the Render web service and PostgreSQL database, obtain demo account passwords, and enable the Groq chatbot.

- Deployment branch: `codex/free-cloud-demo`
- Blueprint: `render.yaml` (both resources explicitly use Free plans)
- Runtime: Python 3.12 with Node.js 22 for the React build; `Dockerfile.demo` is an alternative container build
- Website: `/app/`; health: `/health`; API documentation: `/docs`
- Chat generation is initially disabled until a Groq key is added privately in Render.
- The existing ranking model generates recommendations; retraining is disabled on the demo server.

After deployment the application runs independently of your computer. The free web service sleeps after inactivity and the free database expires after 30 days. See the guide for preparation and troubleshooting.

This is a deployment snapshot, not the complete local development history. Continue normal project development in the original checkout.

