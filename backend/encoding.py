from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F

def mean_pooling(model_output, attention_mask="other"):
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)


class TokenModel():
    def __init__(self, type_info):
        self.tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
        self.model = AutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
        self.type_info = type_info
        if type_info == "emotion":
            self.category = [
                "Happy", "Sad", "Angry", "Afraid", "Disgusted",
                "Surprised", "Calm", "Confused", "Excited", "Bored",
                "Loving", "Lonely"
            ]
        else:
            self.category = ["News & Politics", "Technology & Science", "Gaming",
                        "Entertainment & Media", "Sports & Athletics",
                        "Lifestyle & Hobbies", "Health & Wellness", 
                        "Education & Learning", "Business & Finance", ""
                        "Art & Design", "Travel & Culture", "Community & Support"]
        self.classes = self.__init_category(self.category)

    def __init_category(self, category):
        if self.type_info == "emotion":
            categories = self.tokenizer([f"The emtoion in the text is {item}" for item in category], padding=True, truncation=True, return_tensors='pt')
        else:
            categories = self.tokenizer([f"The genre of the text is {item}" for item in category], padding=True, truncation=True, return_tensors='pt')
        with torch.no_grad():
            model_output = self.model(**categories)
            return F.normalize(mean_pooling(model_output, categories['attention_mask']),dim=1)

    def query(self, inputs: list):
        encoded_input = self.tokenizer(inputs, padding=True, truncation=True, return_tensors='pt')
        with torch.no_grad():
            model_output = self.model(**encoded_input)
            processed_output = F.normalize(mean_pooling(model_output, encoded_input['attention_mask']), dim=1)
            similarity = processed_output @ self.classes.T
            classesMax = torch.argmax(similarity, dim = 1)
            return [self.category[idx] for idx in classesMax.numpy().tolist()]
        
if __name__ == "__main__":
    model = TokenModel()
    sentences = ['Come to play genshin impact right now', 'Iran have attacked pearl harbor last week']
    output = model.query(sentences)
    print(output)