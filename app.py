from flask import Flask, jsonify, request
from flask_cors import CORS
from meeting_reminder import MeetingReminder
from pipeline_status_watcher import PipelineStatusWatcher
from post_a_message import PostAMessage

# instantiate the app
app = Flask(__name__, static_url_path='/')
app.config.from_object(__name__)

# pipeline_status_watcher = PipelineStatusWatcher()
# pipeline_status_watcher.start()
post_a_message = PostAMessage()
meeting_reminder = MeetingReminder()
# enable COR
CORS(app, resources={r'/*': {'origins': '*'}})

@app.route('/api/gitlab-pipeline', methods=['GET'])
def gitlab_pipeline():
    with pipeline_status_watcher.data_lock:
        response = {}
        response['stages'] = pipeline_status_watcher.stages_jobs_map
        response['repository_name'] = pipeline_status_watcher.repository_name
        response['branch_name'] = pipeline_status_watcher.branch_name
        response['update_counter'] = pipeline_status_watcher.update_counter
    return jsonify(response)

@app.route('/api/post-a-message/post', methods=['POST'])
def post_a_message_post():
    response_object = {'status': 'success'}
    json_data = request.get_json()
    print(json_data)
    post_a_message.set_message(request.get_json()['message'])
    response_object['message'] = 'Message sent'
    return jsonify(response_object)

@app.route('/api/post-a-message/get', methods=['GET'])
def post_a_message_get():
    return post_a_message.get_message()

@app.route('/api/get-next-meetings', methods=['GET'])
def get_next_meetings():
    message = ''
    for event in meeting_reminder.get_next_meeting_events():
        message += meeting_reminder.meeting_event_to_str(event) + '\n'
    return message

if __name__ == '__main__':
    app.run()