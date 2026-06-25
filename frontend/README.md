# TinyGuide AI — Frontend

Next.js 14 (App Router) · TypeScript · Tailwind CSS · shadcn/ui.
Mobile-first, warm pastel aesthetic. Runs on **port 3000**.

## Setup

```bash
npm install
cp .env.local.example .env.local   # sets NEXT_PUBLIC_API_URL
```

## Run

```bash
npm run dev      # http://localhost:3000
npm run build    # production build
npm run start    # serve the production build
```

> The backend microservice must be running on port 8000 (see `../backend`).

## Structure

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout + floating nav
│   ├── globals.css         # Warm pastel theme (CSS variables)
│   ├── page.tsx            # 📈 Dashboard
│   ├── milestones/page.tsx # 👶 Milestones
│   ├── vaccines/page.tsx   # 💉 Vaccines
│   └── assistant/page.tsx  # 💬 AI Assistant
├── components/
│   ├── floating-nav.tsx    # Mobile floating bottom nav
│   ├── page-header.tsx
│   └── ui/                 # shadcn/ui primitives (button, card)
└── lib/
    ├── api.ts              # Typed client for the :8000 backend
    ├── hooks.ts            # useFetch / useAction async hooks
    └── utils.ts            # cn() helper
```

## API integration

Every backend call is typed in `lib/api.ts` (request + response contracts) and
consumed through the `useFetch` / `useAction` hooks in `lib/hooks.ts`. The base
URL is read from `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`).
