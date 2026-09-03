import {useEffect, useMemo, useState} from "react";

const API = "/api";
const PAGES = [
  "Dashboard",
  "Projects",
  "Properties",
  "Agents",
  "Templates",
  "Media Library",
  "Video Jobs",
  "Renders",
  "Settings",
];

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      detail = await response.text();
    }
    throw new Error(detail);
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

function Pill({status}) {
  const tone = status === "Completed" ? "ok" : status === "Failed" ? "bad" : "gold";
  return <span className={`pill ${tone}`}>{status}</span>;
}

function mediaKeyForKind(kind) {
  if (kind === "interior") return "interiorPhotos";
  if (kind === "video") return "videoClips";
  if (kind === "agent") return "agentPhoto";
  return "exteriorPhotos";
}

function itemsForIds(media, ids) {
  return (ids || []).map((id) => media.find((item) => item.id === id)).filter(Boolean);
}

function propertyPhotoCount(property) {
  const ids = property?.mediaIds || {};
  return (ids.exteriorPhotos || []).length + (ids.interiorPhotos || []).length;
}

function Dropzone({label, hint, accept, multiple = true, disabled, onFiles}) {
  const [over, setOver] = useState(false);
  return (
    <label
      className={`dropzone ${over ? "over" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(event) => {
        event.preventDefault();
        setOver(false);
        const files = [...event.dataTransfer.files];
        if (files.length) onFiles(files);
      }}
    >
      <strong>{label}</strong>
      <span>{hint}</span>
      <input
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={disabled}
        hidden
        onChange={(event) => {
          const files = [...(event.target.files || [])];
          event.target.value = "";
          if (files.length) onFiles(files);
        }}
      />
    </label>
  );
}

function PhotoStrip({items, empty, onRemove}) {
  if (!items.length) {
    return <p className="muted">{empty}</p>;
  }
  return (
    <div className="photo-strip">
      {items.map((item) => (
        <figure className="photo-tile" key={item.id}>
          {String(item.mime || "").startsWith("image/") ? (
            <img src={`/api/media/${item.id}/file`} alt={item.filename} />
          ) : (
            <div className="photo-fallback">{item.filename}</div>
          )}
          <figcaption>{item.filename}</figcaption>
          {onRemove ? (
            <button type="button" className="photo-remove" onClick={() => onRemove(item.id)}>
              Remove
            </button>
          ) : null}
        </figure>
      ))}
    </div>
  );
}

const EMPTY_PROPERTY = {
  address: "",
  city: "",
  province: "BC",
  postalCode: "",
  price: "",
  bedrooms: "",
  bathrooms: "",
  squareFeet: "",
  propertyType: "Detached",
  description: "",
  features: "",
};

function formFromProperty(property) {
  if (!property?.id) {
    return {...EMPTY_PROPERTY};
  }
  return {
    ...EMPTY_PROPERTY,
    ...property,
    features: Array.isArray(property.features)
      ? property.features.join(", ")
      : property.features || "",
  };
}

function propertyCover(property, media) {
  const first =
    itemsForIds(media, property.mediaIds?.exteriorPhotos)[0] ||
    itemsForIds(media, property.mediaIds?.interiorPhotos)[0];
  return first;
}

function PropertyForm({initial, onSave, onCancel}) {
  const [form, setForm] = useState(() => formFromProperty(initial));
  const set = (key, value) => setForm((current) => ({...current, [key]: value}));
  const editing = Boolean(form.id);
  return (
    <form
      className="form property-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSave({
          ...form,
          features: String(form.features || "")
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
        });
      }}
    >
      <div className="form-grid">
        <div className="span-2">
          <label htmlFor="property-address">ADDRESS</label>
          <input id="property-address" value={form.address} onChange={(e) => set("address", e.target.value)} required />
        </div>
        <div>
          <label htmlFor="property-city">CITY</label>
          <input id="property-city" value={form.city} onChange={(e) => set("city", e.target.value)} required />
        </div>
        <div>
          <label htmlFor="property-province">PROVINCE</label>
          <input id="property-province" value={form.province} onChange={(e) => set("province", e.target.value)} />
        </div>
        <div>
          <label htmlFor="property-postal">POSTAL CODE</label>
          <input id="property-postal" value={form.postalCode} onChange={(e) => set("postalCode", e.target.value)} />
        </div>
        <div>
          <label htmlFor="property-price">PRICE</label>
          <input id="property-price" value={form.price} onChange={(e) => set("price", e.target.value)} required />
        </div>
        <div>
          <label htmlFor="property-type">TYPE</label>
          <input id="property-type" value={form.propertyType} onChange={(e) => set("propertyType", e.target.value)} />
        </div>
        <div>
          <label htmlFor="property-beds">BEDS</label>
          <input id="property-beds" value={form.bedrooms} onChange={(e) => set("bedrooms", e.target.value)} />
        </div>
        <div>
          <label htmlFor="property-baths">BATHS</label>
          <input id="property-baths" value={form.bathrooms} onChange={(e) => set("bathrooms", e.target.value)} />
        </div>
        <div>
          <label htmlFor="property-sqft">SQUARE FEET</label>
          <input id="property-sqft" value={form.squareFeet} onChange={(e) => set("squareFeet", e.target.value)} />
        </div>
        <div className="span-3">
          <label htmlFor="property-description">DESCRIPTION</label>
          <textarea id="property-description" value={form.description} onChange={(e) => set("description", e.target.value)} />
        </div>
        <div className="span-3">
          <label htmlFor="property-features">FEATURES (comma separated)</label>
          <input
            id="property-features"
            value={Array.isArray(form.features) ? form.features.join(", ") : form.features}
            onChange={(e) => set("features", e.target.value)}
          />
        </div>
      </div>
      <div className="row">
        <button className="btn" type="submit">{editing ? "Save changes" : "Create property"}</button>
        {onCancel ? (
          <button className="btn ghost" type="button" onClick={onCancel}>Cancel</button>
        ) : null}
      </div>
    </form>
  );
}

const EMPTY_AGENT = {
  name: "",
  phone: "",
  email: "",
  website: "",
  brokerage: "UPCA Real Estate",
};

function AgentForm({initial, onSave, onCancel}) {
  const [form, setForm] = useState(initial || EMPTY_AGENT);
  const set = (key, value) => setForm((current) => ({...current, [key]: value}));
  const editing = Boolean(form.id);
  return (
    <form
      className="form"
      onSubmit={(event) => {
        event.preventDefault();
        onSave(form);
      }}
    >
      <label>NAME</label>
      <input value={form.name || ""} onChange={(e) => set("name", e.target.value)} required />
      <div className="split">
        <div>
          <label>PHONE</label>
          <input value={form.phone || ""} onChange={(e) => set("phone", e.target.value)} />
        </div>
        <div>
          <label>EMAIL</label>
          <input value={form.email || ""} onChange={(e) => set("email", e.target.value)} />
        </div>
      </div>
      <label>WEBSITE</label>
      <input value={form.website || ""} onChange={(e) => set("website", e.target.value)} />
      <label>BROKERAGE</label>
      <input value={form.brokerage || ""} onChange={(e) => set("brokerage", e.target.value)} />
      <div className="row">
        <button className="btn" type="submit">{editing ? "Save changes" : "Save agent"}</button>
        {editing ? (
          <button className="btn ghost" type="button" onClick={onCancel}>Cancel</button>
        ) : null}
      </div>
    </form>
  );
}

export function App() {
  const [page, setPage] = useState("Dashboard");
  const [error, setError] = useState("");
  const [properties, setProperties] = useState([]);
  const [agents, setAgents] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [media, setMedia] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [projects, setProjects] = useState([]);
  const [renders, setRenders] = useState([]);
  const [settings, setSettings] = useState(null);
  const [editingProperty, setEditingProperty] = useState(null);
  const [propertyScreen, setPropertyScreen] = useState("list");
  const [propertyFormKey, setPropertyFormKey] = useState(0);
  const [editingAgent, setEditingAgent] = useState(null);
  const [agentFormKey, setAgentFormKey] = useState(0);
  const [jobForm, setJobForm] = useState({
    propertyId: "",
    agentId: "",
    templateId: "just-listed",
    format: "9:16",
  });
  const [busy, setBusy] = useState(false);
  const [libraryKind, setLibraryKind] = useState("exterior");
  const [libraryPropertyId, setLibraryPropertyId] = useState("");

  const refresh = async () => {
    const [nextProperties, nextAgents, nextTemplates, nextMedia, nextJobs, nextProjects, nextRenders, nextSettings] =
      await Promise.all([
        request("/properties"),
        request("/agents"),
        request("/templates"),
        request("/media"),
        request("/jobs"),
        request("/projects"),
        request("/renders"),
        request("/settings"),
      ]);
    setProperties(nextProperties);
    setAgents(nextAgents);
    setTemplates(nextTemplates);
    setMedia(nextMedia);
    setJobs(nextJobs);
    setProjects(nextProjects);
    setRenders(nextRenders);
    setSettings(nextSettings);
    setJobForm((current) => ({
      ...current,
      propertyId: current.propertyId || nextProperties[0]?.id || "",
      agentId: current.agentId || nextAgents[0]?.id || "",
      templateId: current.templateId || nextTemplates[0]?.id || "just-listed",
    }));
    setLibraryPropertyId((current) => current || nextProperties[0]?.id || "");
  };

  useEffect(() => {
    let cancelled = false;
    const load = async (attempt = 0) => {
      try {
        await refresh();
      } catch (err) {
        if (!cancelled && attempt < 8) {
          window.setTimeout(() => load(attempt + 1), 750);
          return;
        }
        if (!cancelled) {
          setError(err.message);
        }
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!jobs.some((job) => job.status === "Rendering" || job.status === "Preparing")) {
      return undefined;
    }
    const timer = setInterval(() => {
      request("/jobs").then(setJobs).catch(() => {});
      request("/renders").then(setRenders).catch(() => {});
    }, 2500);
    return () => clearInterval(timer);
  }, [jobs]);

  const counts = useMemo(
    () => ({
      properties: properties.length,
      agents: agents.length,
      jobs: jobs.length,
      completed: jobs.filter((job) => job.status === "Completed").length,
    }),
    [properties, agents, jobs],
  );

  const run = async (work) => {
    setError("");
    setBusy(true);
    try {
      await work();
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const uploadFile = async (file, kind, extra = {}) => {
    const params = new URLSearchParams({kind, filename: file.name});
    if (extra.propertyId) params.set("propertyId", extra.propertyId);
    if (extra.agentId) params.set("agentId", extra.agentId);
    return request(`/media?${params.toString()}`, {
      method: "POST",
      headers: {"Content-Type": file.type || "application/octet-stream"},
      body: file,
    });
  };

  const attachMediaFiles = async (propertyId, files, kind) => {
    const property = properties.find((row) => row.id === propertyId);
    if (!property) {
      throw new Error("Select a property first");
    }
    const key = mediaKeyForKind(kind);
    const mediaIds = {...(property.mediaIds || {})};
    const nextIds = [...(mediaIds[key] || [])];
    for (const file of files) {
      const uploaded = await uploadFile(file, kind, {propertyId});
      nextIds.push(uploaded.id);
    }
    mediaIds[key] = nextIds;
    await request(`/properties/${propertyId}`, {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({...property, mediaIds}),
    });
  };

  const detachPropertyMedia = async (propertyId, mediaId, kind) => {
    const property = properties.find((row) => row.id === propertyId);
    if (!property) return;
    const key = mediaKeyForKind(kind);
    const mediaIds = {...(property.mediaIds || {})};
    mediaIds[key] = (mediaIds[key] || []).filter((id) => id !== mediaId);
    await request(`/properties/${propertyId}`, {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({...property, mediaIds}),
    });
  };

  const attachAgentPhoto = async (agentId, file) => {
    const agent = agents.find((row) => row.id === agentId);
    if (!agent) return;
    const uploaded = await uploadFile(file, "agent", {agentId});
    await request(`/agents/${agentId}`, {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({...agent, photoMediaId: uploaded.id}),
    });
  };

  return (
    <div className="app">
      <aside className="nav">
        <div className="brand">
          <span className="brand-mark" />
          UPCA
        </div>
        <nav>
          {PAGES.map((name) => (
            <button
              key={name}
              className={page === name ? "active" : ""}
              onClick={() => {
                if (name === "Properties") {
                  setPropertyScreen("list");
                  setEditingProperty(null);
                }
                setPage(name);
              }}
            >
              {name}
            </button>
          ))}
        </nav>
      </aside>
      <main className="main">
        <div className="kicker">UPCA REAL ESTATE MARKETING</div>
        {error ? <div className="error">{error}</div> : null}

        {page === "Dashboard" && (
          <>
            <h1>Video Factory</h1>
            <p className="lede">Create listing films from property records, agents, and the Just Listed template. OpenMontage and Backlot stay in place.</p>
            <div className="grid">
              <div className="card"><div className="stat">{counts.properties}<span>PROPERTIES</span></div></div>
              <div className="card"><div className="stat">{counts.agents}<span>AGENTS</span></div></div>
              <div className="card"><div className="stat">{counts.jobs}<span>JOBS</span></div></div>
              <div className="card"><div className="stat">{counts.completed}<span>RENDERS</span></div></div>
            </div>
            <p className="lede" style={{marginTop: 28}}>Listing films use the photos you attach to a property. Open Properties or Media Library to add them.</p>
            <div className="row">
              <button className="btn" onClick={() => setPage("Properties")}>Add listing photos</button>
              <button className="btn ghost" onClick={() => setPage("Video Jobs")}>Create project</button>
              <a className="btn ghost" href="http://127.0.0.1:4750" target="_blank" rel="noreferrer">Open Backlot</a>
            </div>
          </>
        )}

        {page === "Projects" && (
          <>
            <h1>Projects</h1>
            <p className="lede">OpenMontage workspaces created by UPCA. Backlot watches the same folder.</p>
            <table className="table">
              <thead><tr><th>ID</th><th>TITLE</th><th>PIPELINE</th><th>BOARD</th></tr></thead>
              <tbody>
                {projects.map((project) => (
                  <tr key={project.project_id}>
                    <td>{project.project_id}</td>
                    <td>{project.title}</td>
                    <td>{project.pipeline_type}</td>
                    <td><a href={`http://127.0.0.1:4750/p/${project.project_id}`} target="_blank" rel="noreferrer">Board</a></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        {page === "Properties" && propertyScreen === "list" && (
          <>
            <div className="page-head">
              <div>
                <h1>Properties</h1>
                <p className="lede">Listings in a three-column catalog. Open a card to edit details and attach the photos the Just Listed film uses.</p>
              </div>
              <button
                className="btn"
                type="button"
                onClick={() => {
                  setEditingProperty(null);
                  setPropertyFormKey((key) => key + 1);
                  setPropertyScreen("edit");
                }}
              >
                New property
              </button>
            </div>
            {properties.length ? (
              <div className="properties-grid">
                {properties.map((property) => {
                  const cover = propertyCover(property, media);
                  const photos = propertyPhotoCount(property);
                  return (
                    <article className="card property-card" key={property.id}>
                      {cover ? (
                        <img className="thumb" src={`/api/media/${cover.id}/file`} alt={property.address} />
                      ) : (
                        <div className="thumb photo-fallback">No photos</div>
                      )}
                      <h3>{property.address || "Untitled listing"}</h3>
                      <p>{[property.city, property.province].filter(Boolean).join(", ")}{property.price ? ` · ${property.price}` : ""}</p>
                      <p>{property.bedrooms || "—"} bd · {property.bathrooms || "—"} ba · {property.squareFeet || "—"} sf</p>
                      <p>{photos === 1 ? "1 listing photo" : `${photos} listing photos`}</p>
                      <div className="row">
                        <button
                          className="btn"
                          type="button"
                          onClick={() => {
                            setEditingProperty(property);
                            setPropertyScreen("edit");
                          }}
                        >
                          Edit details
                        </button>
                      </div>
                    </article>
                  );
                })}
              </div>
            ) : (
              <p className="muted">No listings yet. Create a property, then add photos on its details page.</p>
            )}
          </>
        )}

        {page === "Properties" && propertyScreen === "edit" && (() => {
          const property = editingProperty?.id
            ? properties.find((row) => row.id === editingProperty.id) || editingProperty
            : null;
          const exteriors = itemsForIds(media, property?.mediaIds?.exteriorPhotos);
          const interiors = itemsForIds(media, property?.mediaIds?.interiorPhotos);
          const clips = itemsForIds(media, property?.mediaIds?.videoClips);
          return (
            <>
              <button
                className="text-link"
                type="button"
                onClick={() => {
                  setEditingProperty(null);
                  setPropertyScreen("list");
                }}
              >
                ← Properties
              </button>
              <h1>{property?.address || "New property"}</h1>
              <p className="lede">
                {property
                  ? "Update listing details and attach the photos the Just Listed film uses."
                  : "Save the listing first, then you can add exterior and interior photos."}
              </p>
              <PropertyForm
                key={property?.id || `new-${propertyFormKey}`}
                initial={property}
                onCancel={() => {
                  setEditingProperty(null);
                  setPropertyScreen("list");
                }}
                onSave={(payload) => run(async () => {
                  const current = properties.find((row) => row.id === payload.id);
                  const body = {
                    ...payload,
                    mediaIds: current?.mediaIds || payload.mediaIds || {},
                  };
                  const saved = payload.id
                    ? await request(`/properties/${payload.id}`, {
                        method: "PUT",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify(body),
                      })
                    : await request("/properties", {
                        method: "POST",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify(body),
                      });
                  setEditingProperty(saved);
                  setPropertyScreen("edit");
                })}
              />
              {property?.id ? (
                <div className="listing-card" style={{marginTop: 36}}>
                  <h4>Exterior photos</h4>
                  <PhotoStrip
                    items={exteriors}
                    empty="No exterior photos yet. Drop files below."
                    onRemove={(id) => run(() => detachPropertyMedia(property.id, id, "exterior"))}
                  />
                  <Dropzone
                    label="Add exterior photos"
                    hint="Click or drop JPG, PNG, or WebP"
                    accept="image/*"
                    disabled={busy}
                    onFiles={(files) => run(() => attachMediaFiles(property.id, files, "exterior"))}
                  />
                  <h4>Interior photos</h4>
                  <PhotoStrip
                    items={interiors}
                    empty="No interior photos yet. Drop files below."
                    onRemove={(id) => run(() => detachPropertyMedia(property.id, id, "interior"))}
                  />
                  <Dropzone
                    label="Add interior photos"
                    hint="Living rooms, kitchen, bedrooms, baths"
                    accept="image/*"
                    disabled={busy}
                    onFiles={(files) => run(() => attachMediaFiles(property.id, files, "interior"))}
                  />
                  <h4>Optional video clips</h4>
                  <PhotoStrip
                    items={clips}
                    empty="No clips attached."
                    onRemove={(id) => run(() => detachPropertyMedia(property.id, id, "video"))}
                  />
                  <Dropzone
                    label="Add walkthrough clips"
                    hint="Optional MP4 / MOV / WebM"
                    accept="video/*"
                    disabled={busy}
                    onFiles={(files) => run(() => attachMediaFiles(property.id, files, "video"))}
                  />
                  <div className="row" style={{marginTop: 28}}>
                    <button
                      className="btn danger"
                      type="button"
                      disabled={busy}
                      onClick={() => {
                        if (!window.confirm(`Remove ${property.address}?`)) return;
                        run(async () => {
                          await request(`/properties/${property.id}`, {method: "DELETE"});
                          setEditingProperty(null);
                          setPropertyScreen("list");
                          setJobForm((current) => (
                            current.propertyId === property.id
                              ? {...current, propertyId: ""}
                              : current
                          ));
                        });
                      }}
                    >
                      Remove listing
                    </button>
                  </div>
                </div>
              ) : null}
            </>
          );
        })()}

        {page === "Agents" && (
          <>
            <h1>Agents</h1>
            <p className="lede">The selected agent appears on the closing card of each Just Listed film.</p>
            <div className="grid">
              {agents.map((agent) => (
                <div className="card" key={agent.id}>
                  {agent.photoMediaId ? (
                    <img className="thumb" src={`/api/media/${agent.photoMediaId}/file`} alt={agent.name} />
                  ) : null}
                  <h3>{agent.name}</h3>
                  <p>{agent.brokerage}</p>
                  <p>{agent.phone}<br />{agent.email}</p>
                  <div className="row" style={{marginBottom: 12}}>
                    <button className="btn ghost" onClick={() => setEditingAgent(agent)}>Edit</button>
                    <button
                      className="btn danger"
                      disabled={busy}
                      onClick={() => {
                        const used = jobs.filter((job) => job.agentId === agent.id).length;
                        const extra = used ? ` ${used} video job${used === 1 ? "" : "s"} used this agent.` : "";
                        if (!window.confirm(`Remove ${agent.name}?${extra}`)) return;
                        run(async () => {
                          await request(`/agents/${agent.id}`, {method: "DELETE"});
                          if (editingAgent?.id === agent.id) setEditingAgent(null);
                          setJobForm((current) => (
                            current.agentId === agent.id
                              ? {...current, agentId: ""}
                              : current
                          ));
                        });
                      }}
                    >
                      Remove
                    </button>
                  </div>
                  <Dropzone
                    label={agent.photoMediaId ? "Replace headshot" : "Add agent photo"}
                    hint="Used on the closing card"
                    accept="image/*"
                    multiple={false}
                    disabled={busy}
                    onFiles={(files) => run(() => attachAgentPhoto(agent.id, files[0]))}
                  />
                </div>
              ))}
            </div>
            <h2 style={{marginTop: 36}}>{editingAgent?.id ? `Edit ${editingAgent.name}` : "New agent"}</h2>
            <AgentForm
              key={editingAgent?.id || `new-${agentFormKey}`}
              initial={editingAgent}
              onCancel={() => setEditingAgent(null)}
              onSave={(payload) => run(async () => {
                const current = agents.find((row) => row.id === payload.id);
                const body = {
                  ...payload,
                  photoMediaId: current?.photoMediaId || payload.photoMediaId || "",
                  logoMediaId: current?.logoMediaId || payload.logoMediaId || "",
                  socialLinks: current?.socialLinks || payload.socialLinks || {},
                };
                if (payload.id) {
                  await request(`/agents/${payload.id}`, {
                    method: "PUT",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify(body),
                  });
                } else {
                  await request("/agents", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify(body),
                  });
                }
                setEditingAgent(null);
                setAgentFormKey((key) => key + 1);
              })}
            />
          </>
        )}

        {page === "Templates" && (
          <>
            <h1>Templates</h1>
            <div className="grid">
              {templates.map((template) => (
                <div className="card" key={template.id}>
                  <h3>{template.name}</h3>
                  <p>{template.videoType} · {template.duration}s · {template.compositionId}</p>
                  <p>{template.audience}</p>
                </div>
              ))}
            </div>
          </>
        )}

        {page === "Media Library" && (
          <>
            <h1>Media Library</h1>
            <p className="lede">Upload listing photos here, or drop them directly on a property. Photos are copied into an OpenMontage project when you generate a video.</p>
            <div className="card" style={{marginBottom: 24, maxWidth: 720}}>
              <div className="split">
                <div>
                  <label>KIND</label>
                  <select value={libraryKind} onChange={(e) => setLibraryKind(e.target.value)}>
                    <option value="exterior">Exterior</option>
                    <option value="interior">Interior</option>
                    <option value="video">Video clip</option>
                    <option value="agent">Agent photo</option>
                  </select>
                </div>
                <div>
                  <label>ATTACH TO PROPERTY</label>
                  <select value={libraryPropertyId} onChange={(e) => setLibraryPropertyId(e.target.value)}>
                    <option value="">Library only</option>
                    {properties.map((property) => (
                      <option key={property.id} value={property.id}>{property.address}</option>
                    ))}
                  </select>
                </div>
              </div>
              <Dropzone
                label="Drop listing photos here"
                hint="Click to browse, or drag several files at once"
                accept={libraryKind === "video" ? "video/*" : "image/*"}
                disabled={busy}
                onFiles={(files) => run(async () => {
                  if (libraryPropertyId && libraryKind !== "agent") {
                    await attachMediaFiles(libraryPropertyId, files, libraryKind);
                    return;
                  }
                  for (const file of files) {
                    await uploadFile(file, libraryKind, libraryKind === "agent" ? {agentId: agents[0]?.id} : {});
                  }
                })}
              />
            </div>
            {media.length ? (
              <div className="grid">
                {media.map((item) => (
                  <div className="card" key={item.id}>
                    {String(item.mime || "").startsWith("image/") ? (
                      <img className="thumb" src={`/api/media/${item.id}/file`} alt={item.filename} />
                    ) : (
                      <div className="thumb photo-fallback">{item.filename}</div>
                    )}
                    <h3>{item.filename}</h3>
                    <p>{item.kind} · {item.id}</p>
                    <button className="btn ghost" disabled={busy} onClick={() => run(async () => {
                      await request(`/media/${item.id}`, {method: "DELETE"});
                    })}>Delete</button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="muted">No files yet. Use the dropzone above or add photos on a property card.</p>
            )}
          </>
        )}

        {page === "Video Jobs" && (
          <>
            <h1>Video Jobs</h1>
            {propertyPhotoCount(properties.find((row) => row.id === jobForm.propertyId)) === 0 ? (
              <p className="error">
                {properties.find((row) => row.id === jobForm.propertyId)?.address || "This listing"} has no photos yet. Add them on Properties or Media Library, then generate — otherwise the film is navy frames with type only.
                {" "}
                <button className="btn ghost" type="button" onClick={() => setPage("Properties")}>Add listing photos</button>
              </p>
            ) : (
              <p className="lede">
                {propertyPhotoCount(properties.find((row) => row.id === jobForm.propertyId))} listing photos attached. Generate after the photos look right.
              </p>
            )}
            <div className="wizard">
              <div>
                <label>PROPERTY</label>
                <select value={jobForm.propertyId} onChange={(e) => setJobForm({...jobForm, propertyId: e.target.value})}>
                  {properties.map((property) => (
                    <option key={property.id} value={property.id}>{property.address}</option>
                  ))}
                </select>
              </div>
              <div>
                <label>AGENT</label>
                <select value={jobForm.agentId} onChange={(e) => setJobForm({...jobForm, agentId: e.target.value})}>
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>{agent.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label>TEMPLATE</label>
                <select value={jobForm.templateId} onChange={(e) => setJobForm({...jobForm, templateId: e.target.value})}>
                  {templates.map((template) => (
                    <option key={template.id} value={template.id}>{template.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label>FORMAT</label>
                <select value={jobForm.format} onChange={(e) => setJobForm({...jobForm, format: e.target.value})}>
                  <option value="9:16">9:16 · 1080x1920</option>
                  <option value="16:9">16:9 · 1920x1080</option>
                  <option value="1:1">1:1 · 1080x1080</option>
                </select>
              </div>
              <div className="row">
                <button className="btn" disabled={busy} onClick={() => run(async () => {
                  const created = await request("/jobs", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify(jobForm),
                  });
                  await request(`/jobs/${created.id}/prepare`, {method: "POST"});
                })}>Generate video</button>
                <button className="btn ghost" disabled={busy} onClick={() => {
                  const latest = jobs[0];
                  if (!latest) return;
                  run(() => request(`/jobs/${latest.id}/render`, {method: "POST"}));
                }}>Render latest</button>
              </div>
            </div>
            <table className="table" style={{marginTop: 32}}>
              <thead><tr><th>JOB</th><th>TITLE</th><th>FORMAT</th><th>STATUS</th><th></th></tr></thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id}>
                    <td>{job.id}</td>
                    <td>{job.title}</td>
                    <td>{job.format}</td>
                    <td><Pill status={job.status} /></td>
                    <td>
                      <button className="btn ghost" disabled={busy} onClick={() => run(() => request(`/jobs/${job.id}/render`, {method: "POST"}))}>
                        Render
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {jobs[0]?.error ? <p className="error">{jobs[0].error}</p> : null}
          </>
        )}

        {page === "Renders" && (
          <>
            <h1>Renders</h1>
            {renders.map((item) => (
              <div className="card" key={item.jobId} style={{marginBottom: 16}}>
                <h3>{item.title}</h3>
                <p>{item.format} · {item.status}</p>
                <video className="player" controls src={`/api/renders/${item.jobId}/file`} />
                <div className="row" style={{marginTop: 12}}>
                  <a className="btn" href={`/api/renders/${item.jobId}/file`} download>Download MP4</a>
                </div>
              </div>
            ))}
          </>
        )}

        {page === "Settings" && settings && (
          <>
            <h1>Settings</h1>
            <form className="form" onSubmit={(event) => {
              event.preventDefault();
              run(() => request("/settings", {
                method: "PUT",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(settings),
              }));
            }}>
              <label>PRIMARY COLOR</label>
              <input value={settings.branding?.primaryColor || ""} onChange={(e) => setSettings({
                ...settings,
                branding: {...settings.branding, primaryColor: e.target.value},
              })} />
              <label>SECONDARY COLOR</label>
              <input value={settings.branding?.secondaryColor || ""} onChange={(e) => setSettings({
                ...settings,
                branding: {...settings.branding, secondaryColor: e.target.value},
              })} />
              <label>DEFAULT CTA</label>
              <input value={settings.cta?.text || ""} onChange={(e) => setSettings({
                ...settings,
                cta: {...settings.cta, text: e.target.value},
              })} />
              <label>DEFAULT FORMAT</label>
              <select value={settings.defaultFormat || "9:16"} onChange={(e) => setSettings({...settings, defaultFormat: e.target.value})}>
                <option value="9:16">9:16</option>
                <option value="16:9">16:9</option>
                <option value="1:1">1:1</option>
              </select>
              <button className="btn" type="submit">Save settings</button>
            </form>
          </>
        )}
      </main>
    </div>
  );
}
