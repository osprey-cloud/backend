
from flask_restful import Resource, request
from app.models.user import User
from app.helpers.activity_logger import filter_logs , get_logs
from flask_jwt_extended import jwt_required, get_jwt_identity


class ActivityFeedView(Resource):
    @jwt_required
    def get(self):
        current_user = User.get_by_id(get_jwt_identity())
        
        params = {
            'general': True,
            'operations': ['Create', 'Update', 'Delete', 'Follow'],
            'statuses': ['Success'],
            'models': ['Project', 'App', 'Database', 'User']
        }
        user_id = request.args.get('user_id', None)
        if user_id:
            user = User.get_by_id(user_id)
            if not user:
                return dict(status='fail', message='User not found'), 404
            params['user_id'] = user_id

        following = current_user.followed.all()
        if following and not user_id:
            params['user_ids'] = [user.id for user in following]

        tags_followed = current_user.followed_tags
        if tags_followed:
            params['a_tag_ids'] = [tag.tag_id for tag in tags_followed]

        
        # get project or app details in each item in the feed and return them
        user_feed = {}
        user_activities = []
        pagination_data = {
            'next_page': 1
        }


        public_activities = []

        while len(public_activities)<= 0 or len(public_activities)< 10:
            print(pagination_data)
            if pagination_data['next_page']:
                user_feed = get_logs({**params , 'page': pagination_data['next_page']})
                if user_feed.status_code != 200:
                    return dict(status='fail', message='Failed to fetch user feed'), 500
                user_feed = user_feed.json()
                user_activities = user_feed.get('data').get('activity')
                pagination_data = user_feed.get('data').get('pagination')
                public_activities.extend(filter_logs(user_activities))
            else:
                break

        user_feed.get('data')['activity'] = public_activities
        return dict(user_feed=user_feed), 200
