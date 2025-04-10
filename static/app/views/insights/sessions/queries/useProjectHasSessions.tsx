import usePageFilters from 'sentry/utils/usePageFilters';
import useProjects from 'sentry/utils/useProjects';

export default function useProjectHasSessions() {
  const {selection} = usePageFilters();
  const {projects: allProjects} = useProjects();

  const projectIds = selection.projects;

  const projects = projectIds.length
    ? projectIds.map(projectId => {
        return allProjects.find(p => p.id === projectId.toString());
      })
    : allProjects;

  const hasSessionData = projects.some(p => p?.hasSessions);

  return hasSessionData;
}
