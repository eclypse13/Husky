import { useParams } from "react-router-dom";
import { useWorkingGroupsRetrieve } from "@/generated/leadership/leadership";

export default function WorkingGroup() {
  const { id } = useParams();
  const { data: response, isLoading, error } = useWorkingGroupsRetrieve(Number(id), {
    query: { enabled: !!id },
  });
  const data = response?.data;

  if (error) return <div>Не удалось загрузить рабочую группу</div>;
  if (isLoading || !data) return <div>Загрузка…</div>;

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
