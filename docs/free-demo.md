# Smart PE — free cloud demonstration

This setup runs the React website, FastAPI backend and a separate fictional PostgreSQL database on Render. A Groq account supplies the optional chatbot language model. After deployment, your computer can be switched off: Render runs the server and visitors only need an internet connection and a browser.

**Deployment verified on 7 October 2026.** The website, teacher/student logins, profiles, workout history, recommendation generation, explanations and chatbot fallback replies passed public HTTP checks. Groq generation remains disabled until you add your own API key. Keep the account passwords privately for the presentation.

| Your resource | Address |
| --- | --- |
| Website | [Smart PE](https://smart-pe-demo.onrender.com/app/) |
| Web service dashboard | [smart-pe-demo](https://dashboard.render.com/web/srv-db30svu0tbcc738b7as0) |
| Private environment settings | [Environment](https://dashboard.render.com/web/srv-db30svu0tbcc738b7as0/env) |
| Demo database dashboard | [smart-pe-demo-db](https://dashboard.render.com/d/dpg-db30qhgm7kps73ckhqrg-a) |

The database's **Internal Database URL** is already configured privately as **`DB_URL`**. Its password is not exposed by the connected integration. For generated chatbot replies, set **`LLM_API_KEY`** privately to your Groq key and **`LLM_ENABLED=true`**, then save/deploy. Do not paste their values into chat or GitHub.

This free database expires on **6 November 2026**. Complete the demonstration before that date.

## 1. Accounts you need

| Service | Purpose | What to select |
| --- | --- | --- |
| [Render](https://dashboard.render.com) | Runs the website and database | Free web service and Free PostgreSQL |
| GitHub | Stores the deployment source | Your existing `alanmusabek/smart-pe` repository |
| [Groq](https://console.groq.com) | Generates chatbot messages | Free account; no Developer upgrade |

You do not need a domain, a paid OpenAI subscription, Django, or a locally installed language model. This deployment keeps FastAPI. The OpenAI Python library in the project is a client for the compatible Groq API; installing it does not install a model.

For a completely free demonstration, keep both Render resources on **Free** and stay within the included usage. Do not enable paid upgrades. If the signup flow requests account verification, complete that in your own browser. Do not send account passwords or API keys through chat. [Render free plans](https://render.com/docs/free) and [Groq billing](https://console.groq.com/docs/billing-faqs) describe the provider rules.

## 2. Create a new deployment (skip if using the resources above)

The deployment branch is `codex/free-cloud-demo`. It contains the application source, model artifact, fictional database initializer and `render.yaml`; it excludes local credentials, student exports, training records and reports.

1. Sign in to Render and connect your GitHub account. Connecting the Render plugin in Codex gives the assistant access to your Render workspace; Render also needs its own connection to GitHub to build the repository.
2. In Render, select **New → Blueprint** and connect `alanmusabek/smart-pe`.
3. Select branch **`codex/free-cloud-demo`**, leaving the Blueprint path as **`render.yaml`**.
4. Review the proposed resources: `smart-pe-demo` web service and `smart-pe-demo-db` PostgreSQL database. Both must say **Free**, in **Frankfurt**. Do not accept a paid plan.
5. Deploy the Blueprint. The build installs the CPU runtime and builds React; the first startup creates the fictional database automatically. Wait for the web service to become live. The first build can take several minutes.
6. Copy the service's actual HTTPS address from Render. Open that address with **`/app/`** at the end. Its **`/health`** endpoint should return a successful JSON response once startup finishes.

These steps follow the [Render Blueprint setup](https://render.com/docs/infrastructure-as-code). Names can acquire suffixes if resources with those names already exist; always use the address displayed for your new web service.

No separate frontend hosting, database migration command, or laptop tunnel is required. Render's Python runtime builds React during deployment and serves it through FastAPI. `.python-version` selects Python 3.12 and `NODE_VERSION=22` selects Node.js. `Dockerfile.demo` remains an alternative container build. The Blueprint supplies the database connection and generates authentication secrets automatically. The database accepts the application's internal Render connection; external access is disabled.

If the resources are created directly through the Render integration instead of a Blueprint, the connector might not expose the database connection URL. In that case, open the demo database in Render, copy its **Internal Database URL**, then paste it privately into the web service's **Environment** variable named **`DB_URL`**. Save and deploy the environment change. The generated authentication secrets and demo passwords are already stored in that same Environment page. Do not send the connection URL through chat or commit it to GitHub. Do not create a second Blueprint for an existing deployment.

## 3. Sign in to the demo

In the web service's **Environment** settings, reveal and copy the securely generated values listed below. Keep the passwords private. A private local copy of the two demo account logins is also saved in `.runtime/render-demo-accounts.txt`; it is excluded from Git.

| Role | Email | Password environment variable |
| --- | --- | --- |
| Teacher | `teacher2@smartpe.edu` | `DEMO_TEACHER_PASSWORD` |
| Student | `student.demo@smartpe.edu` | `DEMO_STUDENT_PASSWORD` |

These are new cloud accounts. Their passwords are independent of the accounts on your original database. The student account belongs to **Demo Student 01**.

The initial dataset has six fictional students, 26 exercises, example health measurements, previous workouts and feedback, and one scheduled workout per student. Existing-model recommendations and explanations are available. Seeded history and assessment thresholds are presentation examples, not measured university results or official standards. Public self-registration is disabled.

Initialization runs only on an empty database. Later startups retain the demo data. If the selected database already contains tables without the demo marker, startup refuses to modify it. Select the new demo database instead of pointing this service at the original project database.

The password environment variables are used on the **first initialization**. Changing them later does not update existing account password hashes. Keep the original values for this presentation; ask for an explicit account password reset if needed.

## 4. Enable the chatbot

The first deployment has language-model generation disabled so the website can start before you obtain an AI key. Database-based responses still work, but they are not generated by Groq.

1. Create a free Groq account and open its [API keys page](https://console.groq.com/keys).
2. Create a key. In Render, open the web service's **Environment** settings and add **`LLM_API_KEY`** with that value. Never put it in GitHub, `render.yaml`, a screenshot or chat.
3. Change **`LLM_ENABLED`** to **`true`**. Keep the following settings:

| Setting | Value |
| --- | --- |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` |
| `LLM_MODEL` | `qwen/qwen3.8-27b` |
| `LLM_REASONING_EFFORT` | `none` |
| `LLM_TIMEOUT` | `15` |
| `LLM_MAX_TOKENS` | `400` |
| `LLM_TEMPERATURE` | `0.7` |

4. Save the environment changes and deploy/restart the service so the process reads them. Wait for it to become live again.
5. Sign in as the student. Start a new conversation and try **“How can I improve my endurance?”** and **“Как улучшить выносливость?”**. Check the chatbot's model status as well as an actual generated reply. A successful model-list check alone does not prove that generation works.

Groq hosts the model, so Ollama does not need to run on Render or your computer. Qwen supports multilingual dialogue; `reasoning_effort=none` selects its faster conversational mode. This is currently a preview model, so its availability can change. Check your account's model list and free quotas before the presentation. [Groq model documentation](https://console.groq.com/docs/model/qwen/qwen3.8-27b) and [rate limits](https://console.groq.com/docs/rate-limits) explain these settings.

With generation enabled, the chatbot sends the fictional student's cached context and recent conversation to Groq. It loads student data from the database at the beginning of a conversation and reuses that snapshot until application changes invalidate it. The external chat API is stateless, so the cached context still accompanies model requests.

**If you created a Blueprint, disable automatic Blueprint syncing after enabling chat.** The initial YAML sets `LLM_ENABLED=false`; syncing it again could overwrite your dashboard change. The resources linked above were created directly and have no Blueprint to sync. Service code auto-deployment is already off. Update the Blueprint deliberately if you later want it to manage the enabled setting.

## 5. How to run it for the dean

Once the cloud service is live, “starting the server” means opening its website. You do not run `uvicorn`, `start-demo.ps1`, Cloudflare or Ollama on your laptop for this version.

**About 10–15 minutes before the demonstration:**

1. Open your saved `/app/` address and let the server wake up.
2. Sign in as the teacher. Check the student list, one profile, workout history and a recommendation.
3. Open a separate browser tab or private window and sign in as the student. Test a chatbot reply in each language.
4. Keep the presentation tab ready. Use the application during the demonstration; a quiet browser tab alone does not guarantee inbound requests.

An hour of normal interaction is a reasonable use of this demo setup, provided the database has not expired and quotas remain. Free hosting does not guarantee uninterrupted availability. Keep a few screenshots as a practical presentation backup.

## 6. Restarting and updating later

Render starts the backend automatically with the configured start command and its assigned port. If a deployment fails, read the service's **Logs** and deployment events in the dashboard first.

To deploy source changes, push an updated deployment snapshot to `codex/free-cloud-demo`, then use the web service's **Manual Deploy** action to deploy the latest commit. Auto-deployment is disabled to avoid a surprise update during the presentation. Ordinary restarts reuse the demo database and the bundled ranking model. A restart clears in-memory chatbot conversations; start a new conversation if the old one expires.

Retraining is deliberately disabled on this small server. The interface explains this, and the API rejects retraining requests. Generating workouts with the existing model remains enabled. Local development retains its original retraining setting.

## 7. Free-plan limits

| Limit | Meaning for this demonstration |
| --- | --- |
| Web service sleeps after 15 minutes without traffic | Open the site before presenting; waking normally takes about a minute, plus application startup. |
| 750 active service hours per workspace per calendar month | Check remaining usage if the workspace runs other free services. |
| Free PostgreSQL expires after 30 days and has 1 GB storage | Present before expiry. This is temporary hosting, not permanent database storage. |
| Free web filesystem is temporary | Workouts live in PostgreSQL; local logs and runtime files can disappear on restart. |
| Provider maintenance/restarts are possible | A free plan has no uninterrupted-demo guarantee. |
| Groq free request/token quotas | Space out prompts. Quota or provider failures produce fallback replies rather than indefinite waiting. |

Free PostgreSQL has no provider backups. Do not rely on it for long-term student records. Check Render's included bandwidth/build usage and Groq's quotas; with no payment method, exhausted Render usage can suspend service or prevent further builds. Provider policies may change. [Render's current limitations](https://render.com/docs/free) and [Groq's account limits](https://console.groq.com/docs/rate-limits) are the authoritative references.

## 8. Troubleshooting

| Symptom | What to check |
| --- | --- |
| Loading page after inactivity | Wait for the free service to wake, then reload. |
| Persistent 502 or failed startup | Read Render logs. Verify the database is available, `DB_URL` is populated, and startup reaches “Application startup complete.” Resource exhaustion or seed errors need a fix before presenting. |
| 401 Unauthorized when signing in | Use the cloud demo email and its original generated password, not a local account password. |
| Model status `disabled` | Set `LLM_ENABLED=true` and redeploy. |
| `authentication_failed` | Check the Groq key in Render privately; replace an invalid or revoked key. |
| `model_missing` | Choose an available free model in your Groq account and update `LLM_MODEL` with compatible reasoning settings. |
| `rate_limited` | Wait for the quota window to reset; avoid repeated rapid prompts. |
| `timeout`, `offline`, `provider_error` or `empty_response` | Check provider availability and configuration. Failed generation has a 30-second cooldown; wait before trying again. |
| Old conversation no longer works | Start a new conversation after restart or expiration. |
| “Refusing to change existing tables” in startup logs | The service is connected to a non-demo database. Correct `DB_URL`; do not delete its existing tables. |
| Site stops working weeks later | Check the demo database creation date and its 30-day expiry. |

To end the demo, suspend the service if available or remove only the resources created for this demonstration. If deleting Blueprint-managed resources, disconnect that Blueprint first so a later sync cannot recreate them. Keep your original project database untouched.
