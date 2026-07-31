class AnalysisService:

    @staticmethod
    def calculate_engagement(post):

        reach = post.get("reach", 0)

        if reach <= 0:

            return 0

        interactions = (

            post.get("likes", 0)

            + post.get("comments", 0)

            + post.get("shares", 0)

            + post.get("saved", 0)

        )

        return round(

            interactions / reach * 100,

            2

        )


    @staticmethod
    def calculate_potential(post):

        engagement = AnalysisService.calculate_engagement(post)

        likes = post.get("likes", 0)

        comments = post.get("comments", 0)

        saved = post.get("saved", 0)

        shares = post.get("shares", 0)

        return round(

            engagement

            + saved * 2

            + shares * 2

            + comments * 1.5

            + likes * 0.2,

            2

        )