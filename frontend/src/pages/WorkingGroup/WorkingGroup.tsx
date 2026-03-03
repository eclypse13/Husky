import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

type Member = {
  id: number;
  name: string;
  position?: string;
  bio_key?: string;
  photo?: string | null;
  email?: string;
  phone?: string;
  order?: number;
};

type WorkingGroup = {
  id: number;
  name: string;
  members: Member[];
};

export default function WorkingGroup() {
  const { id } = useParams();
  const [data, setData] = useState<WorkingGroup | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setError(null);
        const res = await fetch(`/api/working-groups/${id}/`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        setData(json);
      } catch (e) {
        setError("Не удалось загрузить рабочую группу");
      }
    };

    if (id) load();
  }, [id]);

  if (error) return <div>{error}</div>;
  if (!data) return <div>Загрузка…</div>;

  return (
    <div className="working-group">
      <h1>{data.name}</h1>

      <div className="working-group__members">
        {data.members?.map((m) => (
          <div key={m.id} className="working-group__member">
            <div className="working-group__member-name">{m.name}</div>
            {m.position && <div className="working-group__member-role">{m.position}</div>}
            {m.email && <div>{m.email}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
