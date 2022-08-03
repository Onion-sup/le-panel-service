import time
from dateutil import parser
import requests
import threading
import openai
import os
import json

class PipelineStatusWatcher(threading.Thread):
    def __init__(self):
        self.gitlab_host = os.environ["GITLAB_HOST"]
        gitlab_token = os.environ["GITLAB_TOKEN"]
        openai.api_key = os.environ["OPENAI_API_KEY"]
        threading.Thread.__init__(self)
        self._headers = {'PRIVATE-TOKEN': gitlab_token}
        self.data_lock = threading.Lock()
        with self.data_lock:
            self.branch_name = 'null'
            self.repository_name = 'null'
            self.update_counter = 0
            self.stages_jobs_map = {}
            self.pipeline_comment = 'null'

    def _get_project_url(self):
        return 'https://' + self.gitlab_host + '/api/v4/projects'
        
    def _get_project_pipelines_url(self, id_project):
        return 'https://' + self.gitlab_host + '/api/v4/projects/' + str(id_project) + '/pipelines'

    def _get_pipeline_jobs_url(self, pipeline):
        return 'https://' + self.gitlab_host + '/api/v4/projects/' + str(pipeline['project_id']) + '/pipelines/' + str(pipeline['id']) + '/jobs'

    def _get_last_updated_pipeline(self, pipelines):
        pipelines.sort(key=lambda pipeline:parser.parse(pipeline['updated_at']))
        return pipelines[-1]

    def _get_first_updated_pipeline(self, pipelines):
        pipelines.sort(key=lambda pipeline:parser.parse(pipeline['updated_at']))
        return pipelines[0]

    def run(self):
        self.stop = False
        with self.data_lock:
            self.branch_name = 'null'
            self.repository_name = 'null'
            self.update_counter = 0
            self.stages_jobs_map = {}

        update_period = 5
        self.update_counter = 0
        while not self.stop:
            start_t = time.time()    
            time.sleep(0.5)
            self.update()
            update_time = time.time() - start_t
            print('update_time', update_time)
            time.sleep(max([0, update_period - update_time]))

    def update(self):
        running_pipelines = []
        pending_pipelines = []
        ended_pipelines = []
        projects = requests.get(self._get_project_url(), headers=self._headers).json()
        for project in projects:
            project_pipelines = requests.get(self._get_project_pipelines_url(project['id']), headers=self._headers).json()
            for pipeline in project_pipelines:
                if pipeline['status'] == 'running':
                    running_pipelines.append(pipeline)
                elif pipeline['status'] == 'pending':
                    pending_pipelines.append(pipeline)
                else:
                    ended_pipelines.append(pipeline)        
        
        focused_pipeline = None
        if running_pipelines:
            focused_pipeline = self._get_first_updated_pipeline(running_pipelines)
        elif pending_pipelines:
            focused_pipeline = self._get_first_updated_pipeline(pending_pipelines)
        elif ended_pipelines:
            focused_pipeline = self._get_last_updated_pipeline(ended_pipelines)


        pipeline_jobs = requests.get(self._get_pipeline_jobs_url(focused_pipeline), headers=self._headers).json()

        running_jobs = []
        pending_jobs = []
        ended_jobs = []
        stage_jobs_map = {}
        for job in pipeline_jobs:
            if job['status'] == 'running':
                running_jobs.append(job)
            elif job['status'] == 'pending':
                pending_jobs.append(job)
            else:
                ended_jobs.append(job)
        try:
            running_jobs.sort(key=lambda pipeline:parser.parse(pipeline['started_at']))
            pending_jobs.sort(key=lambda pipeline:parser.parse(pipeline['created_at']))
            ended_jobs.sort(key=lambda pipeline:parser.parse(pipeline['finished_at']))
        except Exception as e:
            print('[PipelineStatusWatcher][update] {}'.format(e))
            return

        for job in ended_jobs:
            if job['stage'] not in stage_jobs_map.keys():
                stage_jobs_map[job['stage']] = []
            stage_jobs_map[job['stage']].append(job)
        for job in running_jobs:
            if job['stage'] not in stage_jobs_map.keys():
                stage_jobs_map[job['stage']] = []
            stage_jobs_map[job['stage']].append(job)
        for job in pending_jobs:
            if job['stage'] not in stage_jobs_map.keys():
                stage_jobs_map[job['stage']] = []
            stage_jobs_map[job['stage']].append(job)
        
        target_project = self._get_pipeline_project(projects, focused_pipeline)
        repository_name = self._get_repository_name(target_project)

        branch = self._get_pipeline_branch(focused_pipeline, target_project)
        if branch is not None:
            branch_name = self._get_branch_name(branch)
        else:
            branch_name = focused_pipeline['sha'][:8]

        pipeline_comment = self._get_pipeline_comment()
        with self.data_lock:
            self.stages_jobs_map = {}
            self.repository_name = repository_name
            self.branch_name = branch_name
            self.update_counter += 1
            for stage, job_list in stage_jobs_map.items():
                self.stages_jobs_map[stage] = [{job['name']: job['status']} for job in job_list]
            self.pipeline_comment = pipeline_comment
            print('[update]', self.pipeline_comment)

    def _get_repository_name(self, project):
        repository_name = project['name'].replace('agc-', '')
        repository_name = repository_name.replace('python3-', '')
        return repository_name

    def _get_pipeline_project(self, projects, pipeline):
        return next(project for project in projects if project['id'] == pipeline['project_id'])

    def _get_pipeline_branch(self, pipeline, project):
        url = 'https://' + self.gitlab_host + '/api/v4/projects/' + str(project['id']) + '/repository/branches'
        project_branches = requests.get(url, headers=self._headers).json()
        try:
            branch = next(branch for branch in project_branches if branch['commit']['id'] == pipeline['sha'])
            return branch
        except StopIteration as e:
            print('[PipelineStatusWatcher][_get_pipeline_branch] {}'.format(e))
            return

    def _get_branch_name(self, branch):
        return branch['name'].replace('feature_', '')

    def _get_pipeline_comment(self):
        success_rate = 100
        fail_rate = 0
        progress_status = 20
        openai_instruction = "Bref commentaire rigolo en français d'une pipeline de tests actuellement \
                                à {}% de progression qui pour l'instant a {}% de réussite et {}% d'échec:" \
                                .format(progress_status, success_rate, fail_rate)
        response = openai.Completion.create(
            model="text-davinci-002",
            prompt=openai_instruction,
            temperature=1,
            max_tokens=100
        )
        comment = response.choices[0].text
        comment = comment.strip('\n')
        return comment

    # def first_started_job_list_comparator(self, jobs_1, jobs_2):
    #     min_job_start_date_1 = None
    #     for job in jobs_1:
    #         if job['started_at'] is None:
    #             continue
    #         job_start_date = parser.parse(job['started_at'])
    #         if min_job_start_date_1 is None:
    #             min_job_start_date_1 = job_start_date
            
    #         if min_job_start_date_1 > job_start_date:
    #             min_job_start_date_1 = job_start_date
    #     min_job_start_date_2 = None
    #     for job in jobs_2:
    #         if job['started_at'] is None:
    #             continue
    #         job_start_date = parser.parse(job['started_at'])
    #         if min_job_start_date_2 is None:
    #             min_job_start_date_2 = job_start_date
            
    #         if min_job_start_date_2 > job_start_date:
    #             min_job_start_date_2 = job_start_date
                
    #     print(min_job_start_date_1)
    #     print(min_job_start_date_2)
    #     if min_job_start_date_1 is None:
    #         return True
    #     elif min_job_start_date_2 is None:
    #         return False
    #     else:
    #         return min_job_start_date_1 < min_job_start_date_2

def main():
    pipeline_status_watcher = PipelineStatusWatcher()
    pipeline_status_watcher.update()


if __name__ == '__main__':
    main()