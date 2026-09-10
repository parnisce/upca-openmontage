# UPCA Real Estate Video Factory

Application layer on OpenMontage. Backlot stays on port 4750. This API is 4760. The dashboard is 5173.

## Run

From the OpenMontage repo root, with the existing virtualenv activated:

```powershell
python -m upca.api
```

In another terminal:

```powershell
cd upca/dashboard
npm install
npm run dev
```

Open http://127.0.0.1:5173

## First Just Listed job

1. Properties — confirm or add a listing
2. Upload exterior / interior photos on the property card
3. Video Jobs — choose property, agent, Just Listed, format
4. Generate video (writes an OpenMontage project)
5. Render (Remotion → `projects/<id>/renders/final.mp4`)
6. Optional: open the same project in Backlot at http://127.0.0.1:4750

## Remotion Studio preview

```powershell
cd remotion-composer
npm start
```

Select composition `UPCAJustListed`. Default props are sample listing data, not hardcoded inside the scene components.
